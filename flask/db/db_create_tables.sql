
-- USERS
CREATE TABLE users (
  id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  name          VARCHAR(255) NOT NULL,
  email         VARCHAR(255) NOT NULL,
  reading_speed INT NULL,
  PRIMARY KEY (id),
  UNIQUE (email)
);

-- SHELVES (weak entity owned by users)
CREATE TABLE shelves (
  user_id        INT UNSIGNED NOT NULL,
  shelf_no       INT UNSIGNED NOT NULL,
  background_url TEXT NULL,
  color          VARCHAR(16) NOT NULL DEFAULT '#4287f5',
  PRIMARY KEY (user_id, shelf_no),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- BOOKS
CREATE TABLE books (
  id         INT UNSIGNED NOT NULL AUTO_INCREMENT,
  title      VARCHAR(500) NOT NULL,
  author     VARCHAR(100) NULL,
  year       INT NULL,
  cover_url  TEXT NULL,
  source     VARCHAR(100) NULL,
  genre      VARCHAR(100) NULL,
  project_gutenberg_no INT NULL,
  PRIMARY KEY (id),
  UNIQUE (project_gutenberg_no)
);

-- SHELF_BOOKS 
CREATE TABLE shelf_books (
  user_id   INT UNSIGNED NOT NULL,
  shelf_no  INT UNSIGNED NOT NULL,
  book_id   INT UNSIGNED NOT NULL,
  progress  DECIMAL(5,2) NULL CHECK (progress >= 0 AND progress <= 100),
  PRIMARY KEY (user_id, shelf_no, book_id),
  FOREIGN KEY (user_id, shelf_no) REFERENCES shelves(user_id, shelf_no) ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (book_id)          REFERENCES books(id)
);

-- FOLLOWS (User m:n User, recursive)
CREATE TABLE follows (
  follower_id INT UNSIGNED NOT NULL,
  followee_id INT UNSIGNED NOT NULL,
  PRIMARY KEY (follower_id, followee_id),
  FOREIGN KEY (follower_id) REFERENCES users(id),
  FOREIGN KEY (followee_id) REFERENCES users(id)
);

-- HIGHLIGHTS (private by default)
CREATE TABLE highlights (
  id          INT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id     INT UNSIGNED NOT NULL,
  book_id     INT UNSIGNED NOT NULL,
  text        TEXT NOT NULL,
--   start       INT UNSIGNED NULL,
--   end         INT UNSIGNED NULL,
  timestamp   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  color       VARCHAR(32) NULL,
  PRIMARY KEY (id),
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (book_id) REFERENCES books(id)
);

-- POSTS (Highlight -> Post) 
CREATE TABLE posts (
  id           INT UNSIGNED NOT NULL,
  background   TEXT NULL,
  description  TEXT NULL,
  PRIMARY KEY (id),
  FOREIGN KEY (id) REFERENCES highlights(id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- DISCUSSIONS (Highlight -> Discussion)
CREATE TABLE discussions (
  id          INT UNSIGNED NOT NULL,
  locked      BOOLEAN NOT NULL DEFAULT FALSE,
  visibility  ENUM('public','hidden') NOT NULL DEFAULT 'public',
  PRIMARY KEY (id),
  FOREIGN KEY (id) REFERENCES highlights(id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- COMMENTS
CREATE TABLE comments (
  id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
  discussion_id  INT UNSIGNED NOT NULL,
  user_id        INT UNSIGNED NOT NULL,
  timestamp      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  content        TEXT NOT NULL,
  PRIMARY KEY (id),
  FOREIGN KEY (discussion_id) REFERENCES discussions(id) ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (user_id)       REFERENCES users(id)
);