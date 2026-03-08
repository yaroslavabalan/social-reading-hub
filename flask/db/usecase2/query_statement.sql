SELECT b.genre, AVG(u.reading_speed) AS average_reading_speed
FROM shelves s
LEFT JOIN users u ON u.id = s.user_id
LEFT JOIN shelf_books sb ON sb.user_id = s.user_id AND sb.shelf_no = s.shelf_no
LEFT JOIN books b ON b.id = sb.book_id
WHERE sb.progress = 100
GROUP BY b.genre
ORDER BY average_reading_speed DESC;