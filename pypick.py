from app import create_app, db
from app.models import User, Post, Process, Paramas, Notification, Task

app = create_app()

@app.shell_context_processor 
#registers the function as a shell context function
##allows function to be pre-registes in a flask shell session
def make_shell_context():
    return{'db':db,'User':User,'Post':Post, 'Process':Process, 
           'Paramaters':Paramas, 'Notification': Notification, 'Task':Task}
