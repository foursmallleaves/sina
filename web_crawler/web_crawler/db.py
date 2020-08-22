# coding:utf8
import asyncio
from aiomysql import create_pool, DictCursor


db_pool = {}

# 数据库配置
db_config = {
    'default': {
        'host': '127.0.0.1',
        'port': 3306,
        'user': 'root',
        'password': '',
        'db': '',
        'charset': 'utf8',
        'autocommit': True,
        'maxsize': 10,
        'minsize': 1,
    },
    'other': {
        'host': '127.0.0.1',
        'port': 3306,
        'user': 'root',
        'password': '',
        'db': '',
        'charset': 'utf8',
        'autocommit': True,
        'maxsize': 10,
        'minsize': 1,
    }

}


async def init_db_pool(loop):
    global db_pool
    for dk in db_config.keys():
        config = db_config.get(dk)

        db_pool[dk] = await create_pool(host=config.get('host'), port=config.get('port'),
                                        user=config.get('user'), password=config.get('password'),
                                        db=config.get('db'), loop=loop,
                                        charset=config.get('charset'), autocommit=config.get('autocommit'),
                                        maxsize=config.get('maxsize'), minsize=config.get('minsize'))


async def db_query(sql, args=(), size=None, using='default'):
    _datas = []
    _db_pool = db_pool.get(using)
    async with _db_pool.acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute(sql, args)
            if size:
                _datas = await cur.fetchmany(size)
            else:
                _datas = await cur.fetchall()

            # await db_pool.release(conn)
    return _datas


async def db_query_one(sql, args=(), using='default'):
    _db_pool = db_pool.get(using)
    async with _db_pool.acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute(sql, args)

            return await cur.fetchone()

    return []


async def db_update(sql, args=(), using='default'):
    _db_pool = db_pool.get(using)
    async with _db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, args)
            if cur:
                await cur.rowcount

    return 0


