import os, sqlite3, json, time
from contextlib import contextmanager

DB_PATH = os.getenv("SQLITE_PATH", "airsoft.db")

@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.commit()
    conn.close()

def init_db():
    with db() as conn:
        sql = open(os.path.join(os.path.dirname(__file__), "schema.sql")).read()
        conn.executescript(sql)

def upsert_target(system_id: str, target_id: str, name: str | None = None, seen_ts: float | None = None):
    with db() as conn:
        conn.execute(
            """INSERT INTO targets(system_id, target_id, name, last_seen)
                   VALUES(?,?,?,?)
                   ON CONFLICT(system_id, target_id) DO UPDATE SET
                     name=COALESCE(excluded.name, targets.name),
                     last_seen=COALESCE(excluded.last_seen, targets.last_seen)""" ,
            (system_id, target_id, name, seen_ts or time.time())
        )

def set_target_active(system_id: str, target_id: str, active: int):
    with db() as conn:
        conn.execute("UPDATE targets SET active=? WHERE system_id=? AND target_id=?", (active, system_id, target_id))

def list_targets():
    with db() as conn:
        cur = conn.execute("SELECT * FROM targets ORDER BY system_id, target_id")
        return [dict(r) for r in cur.fetchall()]

def update_target_led(system_id: str, target_id: str, color: str, time_ms: int):
    with db() as conn:
        conn.execute("UPDATE targets SET led_color=?, led_time_ms=? WHERE system_id=? AND target_id=?",
                     (color, time_ms, system_id, target_id))

def create_player(name: str):
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO players(name, created_at) VALUES(?,?)", (name, time.time()))

def list_players():
    with db() as conn:
        cur = conn.execute("SELECT * FROM players ORDER BY name")
        return [dict(r) for r in cur.fetchall()]

def delete_player(pid: int):
    with db() as conn:
        conn.execute("DELETE FROM players WHERE id=?", (pid,))

def create_game(mode: str, params: dict, player_ids: list[int], target_keys: list[str] | None = None):
    with db() as conn:
        cur = conn.execute("INSERT INTO games(mode, params_json, started_ts, active) VALUES(?,?,?,1)",
                           (mode, json.dumps(params), time.time()))
        game_id = cur.lastrowid
        for pid in player_ids:
            conn.execute("INSERT INTO game_players(game_id, player_id, target_key) VALUES(?,?,?)",
                         (game_id, pid, None))
        return game_id

def end_game(game_id: int):
    with db() as conn:
        conn.execute("UPDATE games SET active=0, ended_ts=? WHERE id=?", (time.time(), game_id))

def current_game():
    with db() as conn:
        cur = conn.execute("SELECT * FROM games WHERE active=1 ORDER BY id DESC LIMIT 1")
        r = cur.fetchone()
        return dict(r) if r else None

def record_hit(system_id: str, target_id: str, amp: int | None, player_id: int | None):
    g = current_game()
    with db() as conn:
        conn.execute("INSERT INTO hits(ts, game_id, system_id, target_id, amp, player_id) VALUES(?,?,?,?,?,?)",
                     (time.time(), g['id'] if g else None, system_id, target_id, amp, player_id))

def scores_by_target(active_only: bool = True):
    q = """SELECT system_id, target_id, COUNT(*) AS hits
             FROM hits
             GROUP BY system_id, target_id
             ORDER BY system_id, target_id"""
    with db() as conn:
        cur = conn.execute(q)
        return [dict(r) for r in cur.fetchall()]

def scores_by_player():
    q = """SELECT p.id as player_id, p.name, COUNT(h.id) as hits
             FROM players p LEFT JOIN hits h ON p.id = h.player_id
             GROUP BY p.id, p.name
             ORDER BY hits DESC, p.name"""
    with db() as conn:
        cur = conn.execute(q)
        return [dict(r) for r in cur.fetchall()]
