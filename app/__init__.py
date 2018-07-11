from flask import Flask, request
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_mail import Mail
from flask_babel import Babel
import logging
from logging.handlers import SMTPHandler, RotatingFileHandler
from flask_uploads import UploadSet, ARCHIVES, configure_uploads, IMAGES
import os
from redis import Redis
import rq

'''
What we need to add to this application...
Home page - see upload form that encoorporates date used to save files in new folder.
Path saved in database , given a file ID which is connected to the user. 

Then that file is passed through the 'scriptts.py' which will then process the images

Output.py template will then be rendered with results...

Results.py will be logged on the user's profile page, 
There will be a relational database of outputs connected to each uploaded zip folder. 

Home will show the completeness of laboratory tests. w/ downloadable zip folders 
of all output data for that test...

'''

bootstrap = Bootstrap() #Bootstrap uses three level hiearchy...
login = LoginManager()
login.login_view = 'auth.login' #function or endpoint name for login view
mail = Mail()

db = SQLAlchemy() ##this object represents the database
migrate = Migrate() ##this object represents the migration engine
moment = Moment()

app= Flask(__name__)
photos = UploadSet('photos', IMAGES)
archives = UploadSet('archives', ARCHIVES)
#files = UploadSet('files', FILES)

def create_app(config_class=Config):
    
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    app.config['UPLOADED_PHOTOS_DEST'] = 'app/static/img/'
    configure_uploads(app, photos)
    
    app.config['UPLOADED_ARCHIVES_DEST'] = 'app/static/arch/'
    configure_uploads(app, archives)
    
    # create the folders when setting up your app
    app.config['IMG_PICKED'] = 'app/static/picked/'
     
    # create the folders when setting up your app
    app.config['TO_DOWNLOAD'] = 'app/static/to-download/'
    

    #app.config['UPLOADED_FILES_DEST'] = 'app/static/files/<username>'
    #configure_uploads(app, files)
    
    app.redis = Redis.from_url(app.config['REDIS_URL'])
    app.task_queue = rq.Queue('pypick-tasks', connection=app.redis)
    
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)
    bootstrap.init_app(app)
    moment.init_app(app)

    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    if not app.debug:
        
        if app.config['MAIL_SERVER']:
            auth = None
            if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
                auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            secure = None
            if app.config['MAIL_USE_TLS']:
                secure = ()
            mail_handler = SMTPHandler(
                    mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
                    fromaddr='no-reply@' + app.config['MAIL_SERVER'],
                    toaddrs=app.config['ADMINS'], subject='Microblog Failure',
                    credentials=auth, secure=secure)
            mail_handler.setLevel(logging.ERROR)
            app.logger.addHandler(mail_handler)
        
        if app.config['LOG_TO_STDOUT']:
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(logging.INFO)
            app.logger.addHandler(stream_handler)
        else:
            if not os.path.exists('logs'):
                os.mkdir('logs')
            file_handler = RotatingFileHandler('logs/microblog.log',maxBytes=10240, backupCount=10)
            file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s '
                                        '[in %(pathname)s:%(lineno)d]'))

        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('pyGemPick web app starting up!')
    
    return app

#models defines the structure of the database, routes defines the views of the app


from app import models
