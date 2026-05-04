-- AdvisorScout schema extensions for CS411 project (MySQL).
-- Apply with:  mysql -u root -p academicworld < sql/schema_extensions.sql
-- Or run:     python -m scripts.init_db

-- ---------------------------------------------------------------------------
-- New tables (user-generated data, not part of original AcademicWorld dump)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS faculty_popularity (
  faculty_id INT NOT NULL PRIMARY KEY,
  fav_count INT NOT NULL DEFAULT 0,
  CONSTRAINT fk_popularity_faculty
    FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS user_favorites (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  user_name VARCHAR(255) NOT NULL,
  faculty_id INT NOT NULL,
  added_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_fav_faculty
    FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE,
  CONSTRAINT uq_user_faculty UNIQUE (user_name, faculty_id),
  INDEX idx_fav_user (user_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- (Secondary index idx_fk_keyword_score is created by scripts/init_db.py)

-- ---------------------------------------------------------------------------
-- View: denormalized faculty–keyword–university rows for dashboard queries
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW top_faculty_by_keyword AS
SELECT
  f.id AS faculty_id,
  f.name AS faculty_name,
  f.position,
  u.id AS university_id,
  u.name AS university_name,
  k.id AS keyword_id,
  k.name AS keyword_name,
  fk.score AS keyword_score
FROM faculty_keyword fk
JOIN faculty f ON fk.faculty_id = f.id
JOIN keyword k ON fk.keyword_id = k.id
JOIN university u ON f.university_id = u.id;

-- ---------------------------------------------------------------------------
-- Stored procedure: single-statement body (no DELIMITER needed for pymysql)
-- ---------------------------------------------------------------------------

DROP PROCEDURE IF EXISTS GetTopFacultyForKeyword;

CREATE PROCEDURE GetTopFacultyForKeyword(
  IN p_keyword_name VARCHAR(512),
  IN p_university_id INT,
  IN p_min_score DOUBLE,
  IN p_limit_rows INT
)
  SELECT
    faculty_id,
    faculty_name,
    position,
    university_id,
    university_name,
    keyword_score
  FROM top_faculty_by_keyword
  WHERE keyword_name = p_keyword_name
    AND (p_university_id < 0 OR university_id = p_university_id)
    AND keyword_score >= p_min_score
  ORDER BY keyword_score DESC
  LIMIT p_limit_rows;

-- ---------------------------------------------------------------------------
-- Triggers: maintain aggregate favorite counts (one statement each)
-- ---------------------------------------------------------------------------

DROP TRIGGER IF EXISTS tr_user_favorites_after_insert;

CREATE TRIGGER tr_user_favorites_after_insert
AFTER INSERT ON user_favorites
FOR EACH ROW
  INSERT INTO faculty_popularity (faculty_id, fav_count)
  VALUES (NEW.faculty_id, 1)
  ON DUPLICATE KEY UPDATE fav_count = fav_count + 1;

DROP TRIGGER IF EXISTS tr_user_favorites_after_delete;

CREATE TRIGGER tr_user_favorites_after_delete
AFTER DELETE ON user_favorites
FOR EACH ROW
  UPDATE faculty_popularity
  SET fav_count = GREATEST(0, fav_count - 1)
  WHERE faculty_id = OLD.faculty_id;
