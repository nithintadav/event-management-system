-- =========================================================
-- Event Management System - Normalized Schema
-- =========================================================
DROP DATABASE event_db2;
CREATE DATABASE IF NOT EXISTS event_db2;
USE event_db2;

-- ---------------------------------------------------------
-- USERS
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(20) DEFAULT NULL,
    profile_image VARCHAR(255) DEFAULT NULL,
    role ENUM('user', 'admin') NOT NULL DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ---------------------------------------------------------
-- CATEGORIES (normalizes the old free-text category field)
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB;

INSERT INTO categories (name) VALUES
    ('Technology'), ('Music'), ('Sports'), ('Business'),
    ('Education'), ('Arts & Culture'), ('Health & Wellness')
ON DUPLICATE KEY UPDATE name = name;

-- ---------------------------------------------------------
-- EVENTS
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    slug VARCHAR(220) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    organizer VARCHAR(150) NOT NULL,
    category_id INT DEFAULT NULL,
    venue VARCHAR(200) NOT NULL,
    event_date DATE NOT NULL,
    event_time TIME NOT NULL,
    fee DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    max_seats INT NOT NULL DEFAULT 0,
    banner_image VARCHAR(255) DEFAULT NULL,
    guidelines TEXT DEFAULT NULL,
    contact_email VARCHAR(150) DEFAULT NULL,
    contact_phone VARCHAR(20) DEFAULT NULL,
    status ENUM('upcoming','ongoing','completed','cancelled') NOT NULL DEFAULT 'upcoming',
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------
-- EVENT GALLERY (multiple images per event)
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS event_gallery (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT NOT NULL,
    image_path VARCHAR(255) NOT NULL,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------
-- BOOKINGS (status lets us track cancellations without deleting history)
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    event_id INT NOT NULL,
    status ENUM('confirmed','cancelled') NOT NULL DEFAULT 'confirmed',
    booked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_active_booking (user_id, event_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------
-- WISHLIST
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS wishlist (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    event_id INT NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_wishlist_item (user_id, event_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------
-- NOTIFICATIONS
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    message VARCHAR(255) NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------
-- Seed one admin account (CHANGE THIS PASSWORD IMMEDIATELY)
-- password below is a placeholder hash for "ChangeMe123!" (werkzeug pbkdf2)
-- Generate your own with:
--   python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('yourpassword'))"
-- ---------------------------------------------------------
INSERT INTO users (name, email, password_hash, role)
VALUES ('Admin', 'admin@example.com',
'scrypt:32768:8:1$eHS0Rf5ULjHLyVFp$8b5296fa6095e6f575fe8a04807d7d7806669a640e2a3efe12d5edfb1ca94be5b75e1798e38cd7c6e633cc050e589cf4a89a3e363666b5ee71291df4000b2039', 'admin')
ON DUPLICATE KEY UPDATE name = name;
