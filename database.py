import aiosqlite
import os

class Database:
    def __init__(self, db_path="points.db"):
        self.db_path = db_path

    async def init_db(self):
        # Open a connection to the database
        async with aiosqlite.connect(self.db_path) as db:
            # Create tables
            await db.execute("""
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id INTEGER PRIMARY KEY,
                    audit_channel_id INTEGER
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS moderator_roles (
                    guild_id INTEGER,
                    role_id INTEGER,
                    PRIMARY KEY (guild_id, role_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_points (
                    guild_id INTEGER,
                    user_id INTEGER,
                    points INTEGER DEFAULT 0,
                    PRIMARY KEY (guild_id, user_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS point_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    target_user_id INTEGER,
                    admin_user_id INTEGER,
                    point_change INTEGER,
                    reason TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Save all the table creations we just made
            await db.commit()

# Get the channel ID where audit logs should be sent
    async def get_audit_channel(self, guild_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT audit_channel_id FROM guild_settings WHERE guild_id = ?", (guild_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

 # Save which channel logs should be sent to
    async def set_audit_channel(self, guild_id: int, channel_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO guild_settings (guild_id, audit_channel_id) 
                VALUES (?, ?) 
                ON CONFLICT(guild_id) DO UPDATE SET audit_channel_id=excluded.audit_channel_id
            """, (guild_id, channel_id))
            await db.commit()

# Add, remove or list moderator roles
    async def add_moderator_role(self, guild_id: int, role_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR IGNORE INTO moderator_roles (guild_id, role_id) VALUES (?, ?)", (guild_id, role_id))
            await db.commit()

    async def remove_moderator_role(self, guild_id: int, role_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM moderator_roles WHERE guild_id = ? AND role_id = ?", (guild_id, role_id))
            await db.commit()

    async def get_moderator_roles(self, guild_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT role_id FROM moderator_roles WHERE guild_id = ?", (guild_id,)) as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]

    # Add or remove points for a user and create a record of what happened
    async def add_points(self, guild_id: int, target_user_id: int, admin_user_id: int, amount: int, reason: str):
        async with aiosqlite.connect(self.db_path) as db:
            # Add points to the user
            await db.execute("""
                INSERT INTO user_points (guild_id, user_id, points)
                VALUES (?, ?, ?)
                ON CONFLICT(guild_id, user_id) DO UPDATE SET points = points + excluded.points
            """, (guild_id, target_user_id, amount))
            
            # Record the change in the audit log
            await db.execute("""
                INSERT INTO point_audit (guild_id, target_user_id, admin_user_id, point_change, reason)
                VALUES (?, ?, ?, ?, ?)
            """, (guild_id, target_user_id, admin_user_id, amount, reason))
            
            await db.commit()
            
            # Fetch and return the new total number of points the user has
            async with db.execute("SELECT points FROM user_points WHERE guild_id = ? AND user_id = ?", (guild_id, target_user_id)) as cursor:
                row = await cursor.fetchone()
                return row[0]

    # Check how many points a specific user has
    async def get_points(self, guild_id: int, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT points FROM user_points WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)) as cursor:
                row = await cursor.fetchone()
                # Return their score if they exist or 0 if they haven't gotten any points yet
                return row[0] if row else 0

    # Get a ranked list of the top users with the most points
    async def get_leaderboard(self, guild_id: int, limit: int = 10):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT user_id, points FROM user_points WHERE guild_id = ? ORDER BY points DESC LIMIT ?", (guild_id, limit)) as cursor:
                return await cursor.fetchall()
            
db = Database()