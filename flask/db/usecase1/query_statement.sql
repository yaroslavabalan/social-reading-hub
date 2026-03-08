SELECT
  b.id        AS book_id,
  b.title     AS book_title,
  COUNT(p.id) AS post_count
FROM books b
LEFT JOIN highlights h
  ON h.book_id = b.id
LEFT JOIN posts p
  ON p.id = h.id
GROUP BY b.id, b.title
ORDER BY post_count DESC, b.title;
