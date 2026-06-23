-- PostgreSQL Database Schema
-- Food Health Recommendation System — Phase 1

CREATE TABLE IF NOT EXISTS users (
    id               SERIAL PRIMARY KEY,
    name             VARCHAR(255)        NOT NULL,
    email            VARCHAR(255) UNIQUE NOT NULL,
    password_hash    VARCHAR(255)        NOT NULL,
    age              INTEGER             NOT NULL,
    gender           VARCHAR(20)         NOT NULL,  -- male | female | other
    height           FLOAT               NOT NULL,  -- cm
    weight           FLOAT               NOT NULL,  -- kg
    food_preference  VARCHAR(50)         NOT NULL,  -- vegetarian | non_vegetarian | mixed
    bmi_score        FLOAT,
    bmi_category     VARCHAR(50),
    created_at       TIMESTAMP DEFAULT NOW(),
    updated_at       TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS health_profiles (
    id               SERIAL PRIMARY KEY,
    user_id          INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    -- Hypertension
    hypertension     BOOLEAN DEFAULT FALSE,
    bp_status        VARCHAR(20),           -- normal | low | high
    systolic         INTEGER,
    diastolic        INTEGER,
    -- Diabetes
    diabetes         BOOLEAN DEFAULT FALSE,
    sugar_status     VARCHAR(20),           -- normal | low | high
    fasting_sugar    FLOAT,
    post_meal_sugar  FLOAT,
    -- Thyroid
    thyroid          BOOLEAN DEFAULT FALSE,
    thyroid_type     VARCHAR(30),           -- hypothyroidism | hyperthyroidism
    -- PCOS / PCOD
    pcos             BOOLEAN DEFAULT FALSE,
    pcos_diagnosed   BOOLEAN,
    pcod             BOOLEAN DEFAULT FALSE,
    pcod_diagnosed   BOOLEAN,
    -- Other conditions
    heart_disease    BOOLEAN DEFAULT FALSE,
    kidney_disease   BOOLEAN DEFAULT FALSE,
    obesity          BOOLEAN DEFAULT FALSE,
    none             BOOLEAN DEFAULT FALSE,
    created_at       TIMESTAMP DEFAULT NOW(),
    updated_at       TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS current_health_statuses (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES users(id) ON DELETE CASCADE,
    status_name VARCHAR(100) NOT NULL,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS food_restrictions (
    id               SERIAL PRIMARY KEY,
    user_id          INTEGER REFERENCES users(id) ON DELETE CASCADE,
    restriction_name VARCHAR(255) NOT NULL,
    created_at       TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_health_profiles_user_id ON health_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_current_health_statuses_user_id ON current_health_statuses(user_id);
CREATE INDEX IF NOT EXISTS idx_food_restrictions_user_id ON food_restrictions(user_id);
