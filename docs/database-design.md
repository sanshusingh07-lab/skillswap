# Database design

SQLite is created by SQLAlchemy on first run. The core tables are `users`, `skills`, `user_skills`, `connections`, `messages`, `feedback`, and `notifications`.

`user_skills` is the association table between users and skills. Its `type` column distinguishes `teach` from `learn`, and its unique constraint prevents duplicate entries for the same direction. Connections reference two users and have a pending, accepted, or rejected status. Messages reference sender and receiver. Feedback references the connection that produced it.

Foreign keys, indexes on participant columns, and cascade deletes keep the model easy to query and explain during a viva.
