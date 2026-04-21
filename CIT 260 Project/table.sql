-- 1. Class / Subject Table
CREATE TABLE class (
    ClassID INT AUTO_INCREMENT PRIMARY KEY,
    ClassName VARCHAR(100) NOT NULL
);

-- 2. Physical Locations Table
CREATE TABLE Location (
    LocationID INT AUTO_INCREMENT PRIMARY KEY,
    Campus VARCHAR(100) NOT NULL,
    Building VARCHAR(100) NOT NULL,
    Room VARCHAR(50) NOT NULL
);

-- 3. Schedules and Dates Table
CREATE TABLE Schedules (
    SchedulesID INT AUTO_INCREMENT PRIMARY KEY,
    exam_date DATE NOT NULL,
    exam_time TIME NOT NULL
);

-- 4. Users (Students) Table (Updated based on your image)
CREATE TABLE user (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL
);

-- 5. Central Exams Table
CREATE TABLE Exam (
    ExamID INT AUTO_INCREMENT PRIMARY KEY,
    ClassID INT NOT NULL,
    LocationID INT NOT NULL,
    SchedulesID INT NOT NULL,
    ExamName VARCHAR(100) NOT NULL,
    
    -- Foreign keys pointing to their respective tables
    FOREIGN KEY (ClassID) REFERENCES class(ClassID) ON DELETE CASCADE,
    FOREIGN KEY (LocationID) REFERENCES Location(LocationID) ON DELETE CASCADE,
    FOREIGN KEY (SchedulesID) REFERENCES Schedules(SchedulesID) ON DELETE CASCADE
);

-- 6. Registrations Table
CREATE TABLE Registrations (
    RegistrationsID INT AUTO_INCREMENT PRIMARY KEY,
    UserID INT NOT NULL, -- Keeps your original name 'UserID'
    ExamID INT NOT NULL,
    
    -- Foreign keys: UserID links to the 'id' column in the 'user' table
    FOREIGN KEY (UserID) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (ExamID) REFERENCES Exam(ExamID) ON DELETE CASCADE,
    
    -- Constraint: Prevents the same student from registering twice for the same exam
    CONSTRAINT unique_user_exam UNIQUE (UserID, ExamID)
);

--DELIMITER

-- Rule 1: Limit of 20 students per exam
CREATE TRIGGER check_exam_capacity
BEFORE INSERT ON Registrations
FOR EACH ROW
BEGIN
    DECLARE current_enrollment INT;
    
    -- Count how many students are already registered for this ExamID
    SELECT COUNT(*) INTO current_enrollment 
    FROM Registrations 
    WHERE ExamID = NEW.ExamID;
    
    -- Block insertion if there are already 20 students
    IF current_enrollment >= 20 THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = 'Error: This exam has already reached the maximum limit of 20 students.';
    END IF;
END; //

-- Rule 2: Limit of 3 exams per student
CREATE TRIGGER check_user_exam_limit
BEFORE INSERT ON Registrations
FOR EACH ROW
BEGIN
    DECLARE user_exam_count INT;
    
    -- Count how many exams this UserID is currently registered for
    SELECT COUNT(*) INTO user_exam_count 
    FROM Registrations 
    WHERE UserID = NEW.UserID; -- Fixed to match the UserID column
    
    -- Block insertion if they already have 3 exams
    IF user_exam_count >= 3 THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = 'Error: The student is already registered for the maximum allowed limit of 3 exams.';
    END IF;
END; //

DELIMITER ;


-- test users
INSERT INTO user (username, password_hash)
VALUES ('55555@student.csn.edu', '$2b$12$ggZJJTTwPRMwJRVjjqTs5OddQxtlNPNenJ8g4UdNRdQa5VD.T2arS');

INSERT INTO user (username, password_hash)
VALUES ('44444@student.csn.edu', '$2b$12$wwywXbV9glOwpPLEyGlHMe5MTR2jC4MCNdfJlexmmMCwT/MBzg1AW');