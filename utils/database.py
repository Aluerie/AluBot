from sqlalchemy import Column, Integer, Boolean, String, Float, PickleType, BigInteger, DateTime
from sqlalchemy import create_engine

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from contextlib import contextmanager
from datetime import datetime, timezone

from os import getenv
from dotenv import load_dotenv
load_dotenv(dotenv_path='env.env', verbose=True)
# sql_url = 'postgresql://' + sql_username + ':' + sql_password + '@localhost:5432/postgres'
DATABASE_URL = getenv("SQL_URL")

engine = create_engine(DATABASE_URL, echo=False)  # connect to database,  echo = true to debug
Session = sessionmaker()
Session.configure(bind=engine)
session = Session()
Base = declarative_base()


class DiscordUser(Base):
    __tablename__ = 'GuildMembers'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, default=1234)
    name = Column(String, default='')
    lastseen = Column(DateTime, default=datetime.now(timezone.utc))
    inlvl = Column(Integer, default=1)
    exp = Column(Integer, default=0)
    cur = Column(Integer, default=0)
    rep = Column(Integer, default=0)
    timezone = Column(Float, default=0.0)
    bdate = Column(DateTime)
    msg_count = Column(BigInteger, default=0)
    can_make_tags = Column(Boolean, default=True)


class DiscordEmote(Base):
    __tablename__ = 'GuildEmotes'
    __table_args__ = {'extend_existing': True}
    id = Column(BigInteger, primary_key=True, default=1234)
    name = Column(String, default='')
    animated = Column(Boolean, default=0)
    month_array = Column(PickleType, default=[0]*30)


class botinfo(Base):
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


class DiscordGuilds(Base):
    __tablename__ = 'DiscordGuilds'
    __table_args__ = {'extend_existing': True}
    id = Column(BigInteger, primary_key=True, default=1234)
    name = Column(String, default='')
    milestone_achieved = Column(Integer, default=0)
    suggestion_num = Column(Integer, default=0)
    dota_fav_heroes = Column(PickleType, default=[])
    lol_fav_champs = Column(PickleType, default=[])
    current_timer = Column(Integer, default=0)
    current_important_timer = Column(Integer, default=0)
    current_fact_timer = Column(Integer, default=0)
    current_gif_timer = Column(Integer, default=0)
    current_rule_timer = Column(Integer, default=0)
    irene_is_live = Column(Integer, default=0)
    prefix = Column(String, default='$')
    git_checked_dt = Column(DateTime)


class guildassignment(Base):
    __tablename__ = 'guildassignment'
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


class LeagueAccount(Base):
    __tablename__ = 'LoLAccounts'
    __table_args__ = {'extend_existing': True}
    id = Column(String, primary_key=True, default=1234)
    name = Column(String, default='')
    platform = Column(String, default='')
    accname = Column(String, default='')
    twtv_id = Column(BigInteger, default=None)


class DotaAccount(Base):
    __tablename__ = 'DotaAccounts'
    __table_args__ = {'extend_existing': True}
    id = Column(BigInteger, primary_key=True, default=1234)  # steamid
    name = Column(String, default='')
    friendid = Column(BigInteger, default=1234)
    optin = Column(Integer, default=1)
    twtv_id = Column(BigInteger, default=None)


class RemindersNote(Base):
    __tablename__ = 'RemindersNotes'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, default='')
    userid = Column(BigInteger, default=1234)
    channelid = Column(BigInteger, default=1234)
    dtime = Column(DateTime)


class ToDoNote(Base):
    __tablename__ = 'ToDoNotes'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, default='')
    userid = Column(BigInteger, default=1234)


class AFKNote(Base):
    __tablename__ = 'AFKNote'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, default=1234)  # userid
    name = Column(String, default='')


class WarningData(Base):
    __tablename__ = 'WarningData'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String, default='')  # warn/mute/ban/etc
    name = Column(String, default='')  # type of warning
    dtime = Column(DateTime)
    userid = Column(BigInteger, default=1234)  # banned user id
    modid = Column(BigInteger, default=1234)  # mod user id
    reason = Column(String, default='')  # type of warning


class MuteData(Base):
    __tablename__ = 'MuteData'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    userid = Column(BigInteger, default=1234)
    dtime = Column(DateTime)
    channelid = Column(BigInteger, default=1234)
    reason = Column(String, default='No reason provided')


class mygamerdata(Base):
    __tablename__ = 'mygamerdata'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    last_match_id = Column(BigInteger, default=0)
    match_history = Column(PickleType, default={})


class serverrules(Base):
    __tablename__ = 'serverrules'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(String, default='')


class realrules(Base):
    __tablename__ = 'realrules'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(String, default='')


class tagsdb(Base):
    __tablename__ = 'tagsdb'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, default='')
    owner_id = Column(BigInteger)
    content = Column(String, default='')
    uses = Column(Integer, default=0)
    created_at = Column(DateTime)


class dfmessage(Base):
    __tablename__ = 'dfmessage'
    __table_args__ = {'extend_existing': True}
    id = Column(BigInteger, primary_key=True)  # message id
    match_id = Column(BigInteger)
    ch_id = Column(BigInteger)
    hero_id = Column(Integer)


class lfmessage(Base):
    __tablename__ = 'lfmessage'
    __table_args__ = {'extend_existing': True}
    id = Column(BigInteger, primary_key=True)  # message id
    match_id = Column(String)
    ch_id = Column(BigInteger)
    champ_id = Column(Integer)
    routing_region = Column(String)


Base.metadata.create_all(engine)

# biginteger type of id

m = DiscordUser
e = DiscordEmote
g = DiscordGuilds
b = botinfo
l = LeagueAccount
d = DotaAccount
a = AFKNote
s = mygamerdata
ga = guildassignment
em = dfmessage
lf = lfmessage

# autoincrement type of id
r = RemindersNote
t = ToDoNote
w = WarningData
u = MuteData
sr = serverrules
rr = realrules
tg = tagsdb


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
