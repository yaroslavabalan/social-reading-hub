from db.MongoDBProvider import MongoDBProvider
from db.models import Shelf


class ShelfFactory():
    @staticmethod
    def create_shelf(db, shelf_no, background_url, color, user_id) -> Shelf:
        if isinstance(db, MongoDBProvider):
            data = {
                'user_id': user_id,
                'shelf_no': shelf_no,
                'background_url': background_url,
                'color': color,
            }
            shelf = Shelf(data)
            return shelf
        else:
            data = {
                'shelf_no': shelf_no,
                'background_url': background_url,
                'color': color,
                'user_id': user_id,
            }
            shelf = Shelf(data)
            return shelf