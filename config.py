import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config(object):

    # database security and path
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # pagination
    POSTS_PER_PAGE = 5

    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')

    # recaptcha configuration 
    RECAPTCHA_USE_SSL = False
    RECAPTCHA_PUBLIC_KEY = '6LeKycsZAAAAAPVjWqlPh3nyZdAnKBmyx-Uxvb_I'
    RECAPTCHA_PRIVATE_KEY = '6LeKycsZAAAAAH1_gNE_IJES32lT63WJydcxkF3y'
    RECAPTCHA_OPTIONS = {'theme': 'white'}
