from flask import Flask, request, render_template
import os
import redis
import socket
import logging
from opencensus.ext.azure import metrics_exporter
from opencensus.ext.azure.log_exporter import AzureLogHandler, AzureEventHandler
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.ext.flask.flask_middleware import FlaskMiddleware
from opencensus.stats import stats as stats_module
from opencensus.trace.samplers import ProbabilitySampler
from opencensus.trace.tracer import Tracer

appInsightCnnStr = "InstrumentationKey=c05ca5e3-84f4-45fe-a2ce-ccdd8692c6c2;IngestionEndpoint=https://westus-0.in.applicationinsights.azure.com/;LiveEndpoint=https://westus.livediagnostics.monitor.azure.com/"

logger = logging.getLogger(__name__)
logger.addHandler(AzureLogHandler(connection_string=appInsightCnnStr))
logger.addHandler(AzureEventHandler(connection_string=appInsightCnnStr))
logger.setLevel(logging.INFO)

exporter = metrics_exporter.new_metrics_exporter(enable_standard_metrics=True, connection_string=appInsightCnnStr)
stats = stats_module.stats
view_manager = stats.view_manager
view_manager.register_exporter(exporter)

tracer = Tracer(
    exporter=AzureExporter(connection_string=appInsightCnnStr),
    sampler=ProbabilitySampler(1.0),
)

app = Flask(__name__)

middleware =  FlaskMiddleware(
    app,
    exporter=AzureExporter(connection_string=appInsightCnnStr),
    sampler=ProbabilitySampler(rate=1.0),
)

app.config.from_pyfile('config_file.cfg')

if ("VOTE1VALUE" in os.environ and os.environ['VOTE1VALUE']):
    button1 = os.environ['VOTE1VALUE']
else:
    button1 = app.config['VOTE1VALUE']

if ("VOTE2VALUE" in os.environ and os.environ['VOTE2VALUE']):
    button2 = os.environ['VOTE2VALUE']
else:
    button2 = app.config['VOTE2VALUE']

if ("TITLE" in os.environ and os.environ['TITLE']):
    title = os.environ['TITLE']
else:
    title = app.config['TITLE']

# r = redis.Redis()
redis_server = os.environ['REDIS']
try:
   if "REDIS_PWD" in os.environ:
      r = redis.StrictRedis(host=redis_server,
                        port=6379,
                        password=os.environ['REDIS_PWD'])
   else:
      r = redis.Redis(redis_server)
   r.ping()
except redis.ConnectionError:
   exit('Failed to connect to Redis, terminating.')
   
if not r.get(button1): r.set(button1,0)
if not r.get(button2): r.set(button2,0)

if app.config['SHOWHOST'] == "true":
    title = socket.gethostname()

@app.route('/', methods=['GET', 'POST'])
def index():

    if request.method == 'GET':
        vote1 = r.get(button1).decode('utf-8')
        with tracer.span(name="Total {} Voted: {}".format(button1, vote1)) as span:
            print("Cats Vote")
        
        vote2 = r.get(button2).decode('utf-8')
        with tracer.span(name="Total {} Voted: {}".format(button1, vote1)) as span:
            print("Dogs Vote")
        
        return render_template("index.html", value1=int(vote1), value2=int(vote2), button1=button1, button2=button2, title=title)

    elif request.method == 'POST':
        if request.form['vote'] == 'reset':
            r.set(button1,0)
            r.set(button2,0)

            vote1 = r.get(button1).decode('utf-8')
            properties = {'custom_dimensions': {'Cats Vote': vote1}}
            logger.info("{} voted".format(button1), extra=properties)

            vote2 = r.get(button2).decode('utf-8')
            properties = {'custom_dimensions': {'Dogs Vote': vote2}}
            logger.info("{} voted".format(button2), extra=properties)

            return render_template("index.html", value1=int(vote1), value2=int(vote2), button1=button1, button2=button2, title=title)

        else:
            vote = request.form['vote']
            r.incr(vote,1)
            vote1 = r.get(button1).decode('utf-8')
            vote2 = r.get(button2).decode('utf-8')
            return render_template("index.html", value1=int(vote1), value2=int(vote2), button1=button1, button2=button2, title=title)

if __name__ == "__main__":
    # app.run() 
    app.run(host='0.0.0.0', threaded=True, debug=True)