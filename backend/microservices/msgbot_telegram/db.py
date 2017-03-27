import asyncio
import asyncpg


async def create_table(engine):
    async with engine.acquire() as conn:
        # TODO: Parametrize
        await conn.execute('DROP TABLE IF EXISTS telegram_user_link')
        # aiopg does not have table creation yet
        await conn.execute(
            "CREATE TABLE telegram_user_link ("
            # This id is not a foreign key to anything
            "id serial PRIMARY KEY "
            # Athlete's id
            "user_id integer "
            # Telegram uid, spec says that it's integer
            "telegram_id integer)"



