from db.MongoDBProvider import MongoDBProvider
from db.models.ShelfBook import ShelfBook


class ShelfBookFactory():
    @staticmethod
    def create_shelf(db, shelf_no, book_id, user_id, progress = 0) -> ShelfBook:
        if isinstance(db, MongoDBProvider):
            raise NotImplementedError
        else:
            data = {
                'shelf_no': shelf_no,
                'user_id': user_id,
                'progress': progress,
                'book_id': book_id,
            }
            shelfbook = ShelfBook(data)
            return shelfbook