from flask import Blueprint, render_template, current_app, redirect, url_for, flash, session

from db.MySQLProvider import MySQLProvider
from db.MongoDBProvider import MongoDBProvider
import logging
import os
import random

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

usecase2_bp = Blueprint('usecase2', __name__)

def _extract_indexes_from_plan(plan, indexes=None):
    if indexes is None:
        indexes = set()

    if isinstance(plan, dict):
        if 'indexName' in plan:
            indexes.add(plan['indexName'])
        if 'index' in plan:
            indexes.add(plan['index'])

        if 'indexesUsed' in plan:
            for idx in plan['indexesUsed']:
                indexes.add(idx)

        if 'inputStage' in plan:
            _extract_indexes_from_plan(plan['inputStage'], indexes)
        if 'inputStages' in plan:
            for stage in plan['inputStages']:
                _extract_indexes_from_plan(stage, indexes)

        if 'stages' in plan:
            for stage in plan['stages']:
                _extract_indexes_from_plan(stage, indexes)

        if '$cursor' in plan:
            _extract_indexes_from_plan(plan['$cursor'], indexes)
        if 'queryPlanner' in plan:
            _extract_indexes_from_plan(plan['queryPlanner'].get('winningPlan', {}), indexes)

        if 'rawExplain' in plan:
            _extract_indexes_from_plan(plan['rawExplain'], indexes)

    return indexes

@usecase2_bp.route('/add-indexes', methods=['GET'])
def add_indexes():
    if isinstance(current_app.db, MongoDBProvider):
        db = current_app.db.get_raw_db()

        try:
            db.users.create_index(
                'shelves.books.progress',
                name='idx_users_shelves_books_progress'
            )
            logger.info("Created index idx_users_shelves_books_progress on users(shelves.books.progress)")
        except Exception as e:
            logger.error(f"Error creating index idx_users_shelves_books_progress: {e}")

    return redirect(url_for('usecase2.view'))


@usecase2_bp.route('/drop-indexes', methods=['GET'])
def drop_indexes():
    if isinstance(current_app.db, MongoDBProvider):
        db = current_app.db.get_raw_db()

        try:
            db.users.drop_index('idx_users_shelves_books_progress')
            logger.info("Dropped index idx_users_shelves_books_progress from users collection")
        except Exception as e:
            logger.error(f"Error dropping index idx_users_shelves_books_progress: {e}")

    return redirect(url_for('usecase2.view'))


@usecase2_bp.route('/', methods=['GET'])
def view():
    message = None
    data = []
    stats = {}
    execution_stats = {}

    if isinstance(current_app.db, MySQLProvider):
        sql_file_path = os.path.join(os.path.dirname(__file__), '..', 'db', 'usecase2', 'query_statement.sql')

        try:
            with open(sql_file_path, 'r') as sql_file:
                query = sql_file.read().strip()

            results = current_app.db.execute_query(query)
            data = results if results else []
            message = "Report executed successfully."

        except Exception as e:
            logger.error(f"Error executing usecase2 report: {e}")
            message = f"Failed to execute report: {str(e)}"

    elif isinstance(current_app.db, MongoDBProvider):
        try:
            db = current_app.db.get_raw_db()

            pipeline = [
                # filter relevant users (to lessen the load on the $unwind operations)
                {'$match': {'shelves.books.progress': 100}},

                {'$unwind': '$shelves'},
                {'$unwind': '$shelves.books'},

                # filter only completed books
                {'$match': {'shelves.books.progress': 100}},

                # join with books
                {'$lookup': {
                    'from': 'books',
                    'localField': 'shelves.books.book_id',
                    'foreignField': '_id',
                    'as': 'book_details'
                }},

                {'$unwind': '$book_details'},

                # group by genre and calculate average reading speed
                {'$group': {
                    '_id': '$book_details.genre',
                    'average_reading_speed': {'$avg': '$reading_speed'}
                }},

                # sort results
                {'$sort': {'average_reading_speed': -1}},

                # format output
                {'$project': {
                    '_id': 0,
                    'genre': '$_id',
                    'average_reading_speed': 1
                }}
            ]

            results = list(db.users.aggregate(pipeline))
            data = results if results else []
            message = "Report executed successfully."

            try:
                explain_cmd = {
                    'explain': {
                        'aggregate': 'users',
                        'pipeline': pipeline,
                        'cursor': {}
                    },
                    'verbosity': 'executionStats'
                }
                explain_result = db.command(explain_cmd)

                exec_stats = None
                query_planner = None

                first_stage = explain_result['stages'][0]
                cursor_stage = first_stage.get('$cursor', {})

                if 'executionStats' in cursor_stage:
                    exec_stats = cursor_stage['executionStats']
                if 'queryPlanner' in cursor_stage:
                    query_planner = cursor_stage['queryPlanner']

                if exec_stats is None and 'executionStats' in explain_result:
                    exec_stats = explain_result['executionStats']
                if query_planner is None and 'queryPlanner' in explain_result:
                    query_planner = explain_result['queryPlanner']

                if exec_stats:
                    execution_stats['totalDocsExamined'] = exec_stats.get('totalDocsExamined', 'N/A')
                    execution_stats['totalKeysExamined'] = exec_stats.get('totalKeysExamined', 'N/A')
                    execution_stats['executionTimeMillis'] = exec_stats.get('executionTimeMillis', 'N/A')
                    execution_stats['nReturned'] = exec_stats.get('nReturned', 'N/A')
                else:
                    logger.warning(f"Could not find executionStats. Explain keys: {list(explain_result.keys())}")
                    if 'stages' in explain_result and explain_result['stages']:
                        logger.warning(f"First stage keys: {list(explain_result['stages'][0].keys())}")

                if query_planner:
                    winning_plan = query_planner.get('winningPlan', {})
                    execution_stats['indexesUsed'] = _extract_indexes_from_plan(winning_plan)
                else:
                    execution_stats['indexesUsed'] = _extract_indexes_from_plan(explain_result)

                execution_stats['rawExplain'] = explain_result
            except Exception as explain_error:
                logger.warning(f"Could not get explain stats: {explain_error}")
                execution_stats['error'] = str(explain_error)

        except Exception as e:
            logger.error(f"Error executing usecase2 MongoDB query: {e}")
            message = f"Failed to execute query: {str(e)}"

    if execution_stats and not message:
        message = "Statistics available below."

    return render_template("usecase2/index.html",
                           message=message,
                           data=data,
                           stats=stats,
                           execution_stats=execution_stats
                           )

@usecase2_bp.route('/simulate', methods=['POST'])
def simulate():
    from routes.books import usecase_update_progress

    simulation_stats = {}

    try:
        if isinstance(current_app.db, MySQLProvider):
            incomplete_books_query = """
            SELECT sb.user_id, sb.shelf_no, sb.book_id, sb.progress
            FROM shelf_books sb
            JOIN users u ON u.id = sb.user_id
            WHERE sb.progress < 100 AND sb.progress > 0
            ORDER BY RAND()
            LIMIT 15;
            """

            incomplete_books = current_app.db.execute_query(incomplete_books_query)

            if incomplete_books:
                for book in incomplete_books:
                    current_progress = float(book['progress'])
                    progress_increment = random.uniform(10, 60)
                    new_progress = min(100.0, current_progress + progress_increment)
                    session_reading_speed = random.randint(80, 400)

                    usecase_update_progress(
                        shelf_no=book['shelf_no'],
                        book_id=book['book_id'],
                        new_reading_speed=session_reading_speed,
                        new_progress=new_progress,
                        user_id=book['user_id']
                    )

                logger.info(f"Simulated reading sessions for {len(incomplete_books)} books")

        elif isinstance(current_app.db, MongoDBProvider):
            db = current_app.db.get_raw_db()

            pipeline = [
                {'$match': {
                    'shelves.books.progress': {'$gt': 0, '$lt': 100}
                }},

                {'$unwind': '$shelves'},
                {'$unwind': '$shelves.books'},

                {'$match': {
                    '$and': [
                        {'shelves.books.progress': {'$lt': 100}},
                        {'shelves.books.progress': {'$gt': 0}}
                    ]
                }},
                {'$sample': {'size': 15}},
                {'$project': {
                    '_id': 1,
                    'reading_speed': 1,
                    'shelf_no': '$shelves.shelf_no',
                    'book_id': '$shelves.books.book_id',
                    'progress': '$shelves.books.progress'
                }}
            ]

            incomplete_books = list(db.users.aggregate(pipeline))

            if incomplete_books:
                for book in incomplete_books:
                    current_progress = float(book['progress'])
                    progress_increment = random.uniform(10, 60)
                    new_progress = min(100.0, current_progress + progress_increment)
                    session_reading_speed = random.randint(80, 400)

                    usecase_update_progress(
                        shelf_no=book['shelf_no'],
                        book_id=str(book['book_id']),
                        new_reading_speed=session_reading_speed,
                        new_progress=new_progress,
                        user_id=book['_id']
                    )

                logger.info(f"Simulated reading sessions for {len(incomplete_books)} books")

        logger.info("Use case 2 simulation completed successfully")
    except Exception as e:
        logger.error(f"Error during use case 2 simulation: {e}")

    if simulation_stats:
        session['simulation_stats'] = simulation_stats

    return redirect(url_for('usecase2.view'))
