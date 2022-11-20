from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, Boolean, String, Float, PickleType, BigInteger, DateTime
)
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config import ELENON_URL

engine = create_engine(ELENON_URL, echo=False,)  # connect to database,  echo = true to debug
Session = sessionmaker()
Session.configure(bind=engine)
session = Session()
Base = declarative_base()


class Tags(Base):
    __tablename__ = 'tags'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, default='')
    owner_id = Column(BigInteger)
    content = Column(String, default='')
    uses = Column(Integer, default=0)
    created_at = Column(DateTime)


class Users(Base):
    __tablename__ = 'users'
    __table_args__ = {'extend_existing': True}
    id = Column(BigInteger, primary_key=True, default=1234)
    name = Column(String(256), default='')
    lastseen = Column(DateTime, default=datetime.now(timezone.utc))
    inlvl = Column(Integer, default=1)
    exp = Column(Integer, default=0)
    cur = Column(Integer, default=0)
    rep = Column(Integer, default=0)
    timezone = Column(Float, default=0.0)
    bdate = Column(DateTime)
    msg_count = Column(BigInteger, default=0)
    can_make_tags = Column(Boolean, default=True)


class Emotes(Base):
    __tablename__ = 'emotes'
    __table_args__ = {'extend_existing': True}
    id = Column(BigInteger, primary_key=True, default=1234)
    name = Column(String(256), default='')
    animated = Column(Boolean, default=0)
    month_array = Column(PickleType, default=[0] * 30)


class BotInfo(Base):
    __tablename__ = 'botinfo'
    __table_args__ = {'extend_existing': True}
    id = Column(BigInteger, primary_key=True, default=1)
    milestone_achieved = Column(Integer, default=100)
    suggestion_num = Column(Integer, default=126)
    curr_timer = Column(Integer, default=0)
    curr_important_timer = Column(Integer, default=0)
    curr_fact_timer = Column(Integer, default=0)
    curr_gif_timer = Column(Integer, default=0)
    curr_rule_timer = Column(Integer, default=0)
    git_checked_dt = Column(DateTime, default=datetime.now(timezone.utc))
    trusted_ids = Column(PickleType, default=[])
    irene_is_live = Column(Integer, default=0)
    lol_patch = Column(String, default='')
    dota_patch = Column(String, default='')


class Guilds(Base):
    __tablename__ = 'guilds'
    __table_args__ = {'extend_existing': True}
    id = Column(BigInteger, primary_key=True)
    name = Column(String, default='')
    prefix = Column(String, default='$')
    emote_logs_id = Column(BigInteger, default=None)
    dotafeed_ch_id = Column(BigInteger, default=None)
    dotafeed_hero_ids = Column(PickleType, default=[])
    dotafeed_stream_ids = Column(PickleType, default=[])
    dotafeed_spoils_on = Column(Boolean, default=True)
    lolfeed_ch_id = Column(BigInteger, default=None)
    lolfeed_champ_ids = Column(PickleType, default=[])
    lolfeed_stream_ids = Column(PickleType, default=[])
    lolfeed_spoils_on = Column(Boolean, default=True)


class LoLAccounts(Base):
    __tablename__ = 'lolaccs'
    __table_args__ = {'extend_existing': True}
    id = Column(String, primary_key=True, default=1234)
    name = Column(String, default='')
    platform = Column(String, default='')
    accname = Column(String, default='')
    twtv_id = Column(BigInteger, default=None)
    last_edited = Column(String, default='')  # only exists bcs Riot API is not precise
    fav_id = Column(Integer)


class DotaAccounts(Base):
    __tablename__ = 'dotaaccs'
    __table_args__ = {'extend_existing': True}
    id = Column(BigInteger, primary_key=True, default=1234)  # steamid
    name = Column(String(256), default='')
    friendid = Column(BigInteger, default=1234)
    twtv_id = Column(BigInteger, default=None)
    fav_id = Column(Integer)
    display_name = Column(String(256))


class Reminders(Base):
    __tablename__ = 'reminders'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, default='')
    userid = Column(BigInteger, default=1234)
    channelid = Column(BigInteger, default=1234)
    dtime = Column(DateTime)


class ToDoNotes(Base):
    __tablename__ = 'todonotes'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, default='')
    userid = Column(BigInteger, default=1234)


class AFKNotes(Base):
    __tablename__ = 'afknotes'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, default=1234)  # userid
    name = Column(String, default='')


class Warnings(Base):
    __tablename__ = 'warnings'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String, default='')  # warn/mute/ban/etc
    name = Column(String, default='')  # type of warning
    dtime = Column(DateTime)
    userid = Column(BigInteger, default=1234)  # banned user id
    modid = Column(BigInteger, default=1234)  # mod user id
    reason = Column(String, default='')  # type of warning


class Mutes(Base):
    __tablename__ = 'mutes'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    userid = Column(BigInteger, default=1234)
    dtime = Column(DateTime)
    channelid = Column(BigInteger, default=1234)
    reason = Column(String, default='No reason provided')


class ServerRules(Base):
    __tablename__ = 'serverrules'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(String, default='')


class RealRules(Base):
    __tablename__ = 'realrules'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(String, default='')


class DFMatches(Base):
    __tablename__ = 'dfmatches'
    __table_args__ = {'extend_existing': True}
    id = Column(BigInteger, primary_key=True)  # message id
    match_id = Column(BigInteger)
    ch_id = Column(BigInteger)
    hero_id = Column(Integer)
    twitch_status = Column(String)


class LFMatches(Base):
    __tablename__ = 'lfmatches'
    __table_args__ = {'extend_existing': True}
    id = Column(BigInteger, primary_key=True)  # message id
    match_id = Column(String)
    ch_id = Column(BigInteger)
    champ_id = Column(Integer)
    routing_region = Column(String)


class DotaHistory(Base):
    __tablename__ = 'dotahistory'
    __table_args__ = {'extend_existing': True}
    id = Column(BigInteger, primary_key=True)
    hero_id = Column(Integer)
    winloss = Column(Boolean)
    mmr = Column(Integer)
    role = Column(Integer)
    dtime = Column(DateTime)
    patch = Column(String)
    patch_letter = Column(String)
    custom_note = Column(String)


Base.metadata.create_all(engine)

# biginteger type of id

m = Users
e = Emotes
b = BotInfo
l = LoLAccounts
d = DotaAccounts
a = AFKNotes
ga = Guilds
em = DFMatches
lf = LFMatches
dh = DotaHistory

# autoincrement type of id
r = Reminders
t = ToDoNotes
w = Warnings
u = Mutes
sr = ServerRules
rr = RealRules
tg = Tags


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    ses = Session()
    try:
        yield ses
        ses.commit()
    except Exception as exc:
        ses.rollback()
        print('database.py ;;;', exc)
        raise exc  # probably we should leave it here uncommented ;
    finally:
        ses.close()


def get_value(dbclass, userid, field):
    user = session.query(dbclass).filter_by(id=userid).first()
    return getattr(user, field)


##########################################################################


def add_row(dbclass, id_, **kwargs):  # for static BigInteger databases
    with session_scope() as ses:
        db_row = dbclass(id=id_)
        ses.add(db_row)
        for field, value in kwargs.items():
            setattr(db_row, field, value)


def append_row(dbclass, **kwargs):  # for autoincrement id databases
    with session_scope() as ses:
        db_row = dbclass()
        ses.add(db_row)
        for field, value in kwargs.items():
            setattr(db_row, field, value)


def remove_row(dbclass, userid):
    with session_scope() as ses:
        ses.query(dbclass).filter_by(id=userid).delete()


def set_value(dbclass, userid, **kwargs):
    with session_scope() as ses:
        for row in ses.query(dbclass).filter_by(id=userid):
            for field, value in kwargs.items():
                setattr(row, field, value)


def set_value_by_name(dbclass, name, **kwargs):
    with session_scope() as ses:
        for row in ses.query(dbclass).filter_by(name=name):
            for field, value in kwargs.items():
                setattr(row, field, value)


def inc_value(dbclass, userid, field, value=1):
    with session_scope() as ses:
        user = ses.query(dbclass).filter_by(id=userid).first()
        cur_value = getattr(user, field)
        setattr(user, field, cur_value + value)
    return cur_value + value
