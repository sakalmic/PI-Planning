import json
from flask import Flask, render_template, request, redirect, url_for, session

import warnings
import os
import glob

import jiraif
import user.user as user

warnings.filterwarnings("ignore")

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config.from_object(__name__)

allUsers = {}


@app.before_request
def before_request():
    if not request.is_secure:
        url = request.url.replace('http://', 'https://', 1)
        code = 301
        return redirect(url, code=code)


@app.route("/")
def main():
    if 'username' not in session or not allUsers[session['username']]:
        template = render_template("login.html")
    else:
        template = redirect(url_for('planning'))

    return template


# Route for handling the login page logic
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None

    if request.method == 'POST':
        if request.form['username'] == '' or request.form['password'] == '':
            error = 'Invalid Credentials. Please try again.'
            template = render_template("login.html", error=error)
        else:
            myUser = user.User(request.form['username'], request.form['password'])
            allUsers[request.form['username']] = myUser
            session['username'] = request.form['username']
            template = render_template("index.html")
    else:
        template = render_template("login.html", error=error, menu="False")

    return template


@app.route('/index', methods=['GET'])
def index():
    try:
        if session.get("username", False):
            if allUsers[session.get("username")]:
                template = render_template("index.html")
            else:
                template = redirect(url_for("login"))
        else:
            template = redirect(url_for("login"))
    except:
        template = redirect(url_for('login'))

    return template


@app.route('/logout', methods=['GET'])
def logout():
    # remove the username from the session if it is there
    allUsers.pop(session['username'])
    session.pop('username', None)

    return redirect(url_for('login'))


@app.route("/pip", methods=['GET'])
def planning():
    if 'username' not in session or not allUsers[session['username']]:
        template = redirect(url_for('login'))
    else:
        template = render_template("pip-helper.html")

    return template


@app.route("/stat", methods=['GET'])
def stats():
    if 'username' not in session or not allUsers[session['username']]:
        template = redirect(url_for('login'))
    else:
        template = render_template("pi-stats.html")

    return template


# Get all Tickets from a Sprint in JIRA
@app.route('/api/tickets', methods=['GET'])
def getTickets():
    safefeatures = []
    testitems = []
    actionitems = []
    problemreports = []
    supportitems = []

    year = request.args.get("year")
    team = request.args.get("team")
    pi = request.args.get("pi")

    teamlabel = f"XVP-TEAM-{team}"
    pilabel = f"PI-{year}-0{pi[-1]}"
    error = False

    activeUser = allUsers[session['username']]

    # SAFE FEATURES #
    try:
        features = jiraif.search(activeUser.get_session(), False,
                                 f"project=PVCSX AND fixVersion='{pilabel}' AND type = 'SAFe Feature'")

        for feature in features['issues']:
            if 'issuelinks' in feature['fields']:
                teamepics = []

                for link in feature['fields']['issuelinks']:
                    if 'inwardIssue' in link:
                        if link['inwardIssue']['fields']['issuetype']['name'] == "Epic" and \
                                f"{team}:" in link['inwardIssue']['fields']['summary'] and \
                                link['inwardIssue']['fields']['status']['name'] not in ['Closed', 'Resolved']:
                            epic = {
                                "key": link['inwardIssue']['key'],
                                "summary": link['inwardIssue']['fields']['summary']
                            }
                            teamepics.append(epic)

                if teamepics:
                    linkedepics = []

                    for epic in teamepics:
                        stories = jiraif.search(activeUser.get_session(), False,
                                                f"'Epic Link' = {epic['key']} AND labels != TECHNICAL_DEBT "
                                                "AND labels != R10_TECH_DEBT")
                        linkedstories = []

                        for story in stories['issues']:
                            sprintdescription = story['fields']['customfield_11200']

                            sprintname = ""
                            if sprintdescription:
                                for sprint in sprintdescription:
                                    sprintstate = sprint[sprint.find("state") + 6:sprint.find("name") - 1]
                                    sprintname = sprint[sprint.find("name") + 5:sprint.find(",", sprint.find("name"))]

                                    if sprintstate == "FUTURE":
                                        break

                            linkedstory = {
                                "key": story['key'],
                                "summary": story['fields']['summary'],
                                "storypoints": round(story['fields']['customfield_10003'],2),
                                "labels": story['fields']['labels'],
                                "sprint": sprintname
                            }
                            linkedstories.append(linkedstory)

                        linkedepic = {
                            "key": epic['key'],
                            "summary": epic['summary'],
                            "stories": linkedstories
                        }
                        linkedepics.append(linkedepic)

                    issue = {
                        "key": feature['key'],
                        "summary": feature['fields']['summary'],
                        "epics": linkedepics
                    }
                    safefeatures.append(issue)
    except:
        safefeatures = []
        error = True

    # STORIES W/O SAFE FEATURES #
    try:
        stories = jiraif.search(activeUser.get_session(), False,
                                 f"project=PVCSX AND labels in (STORY_WITHOUT_SAFEFEATURE) AND "
                                 f"labels not in (SYSTEM_TEST, TECHNICAL_DEBT, R10_TECH_DEBT) AND "
                                 f"'Epic Link' is EMPTY AND type=Story AND "
                                 f"labels={teamlabel} AND status not in (Closed, 'Closed (Editable)', Resolved)")

        linkedepics = []
        linkedstories = []
        for story in stories['issues']:
            sprintdescription = story['fields']['customfield_11200']

            sprintname = ""
            if sprintdescription:
                for sprint in sprintdescription:
                    sprintstate = sprint[sprint.find("state") + 6:sprint.find("name") - 1]
                    sprintname = sprint[sprint.find("name") + 5:sprint.find(",", sprint.find("name"))]

                    if sprintstate == "FUTURE":
                        break

            linkedstory = {
                "key": story['key'],
                "summary": story['fields']['summary'],
                "storypoints": story['fields']['customfield_10003'],
                "labels": story['fields']['labels'],
                "sprint": sprintname
            }
            linkedstories.append(linkedstory)

        linkedepic = {
            "key": "PVCSX-XXXXX",
            "summary": "NO EPIC",
            "stories": linkedstories
        }
        linkedepics.append(linkedepic)

        issue = {
            "key": "SAFE-XXXXX",
            "summary": "NO SAFE FEATURE",
            "epics": linkedepics
        }
        safefeatures.append(issue)

    except:
        error = True

    # PROBLEM REPORTS #
    try:
        reports = jiraif.search(activeUser.get_session(), False,
                                "project=PVCSX AND (type = 'Problem Report' OR (type = Story AND "
                                "labels = PROBLEM_REPORT)) AND "
                                f"labels = {teamlabel} AND status not in (Closed, 'Closed (Editable)', Resolved)")

        for report in reports['issues']:
            sprintdescription = report['fields']['customfield_11200']

            sprintname = ""
            if sprintdescription:
                for sprint in sprintdescription:
                    sprintstate = sprint[sprint.find("state") + 6:sprint.find("name") - 1]
                    sprintname = sprint[sprint.find("name") + 5:sprint.find(",", sprint.find("name"))]

                    if sprintstate == "FUTURE":
                        break

            problemreport = {
                "key": report['key'],
                "summary": report['fields']['summary'],
                "storypoints": report['fields']['customfield_10003'],
                "labels": report['fields']['labels'],
                "sprint": sprintname
            }
            problemreports.append(problemreport)

    except:
        problemreports = []
        error = True

    # TECHNICAL DEBT #
    try:
        items = jiraif.search(activeUser.get_session(), False,
                              "project=PVCSX AND type=Story AND (labels in (TECHNICAL_DEBT, "
                              "R10_TECH_DEBT, ACTION_ITEM) AND labels != PROBLEM_REPORT AND labels != SPIKE_NEEDED) AND "
                              f"labels={teamlabel} AND status not in (Closed, 'Closed (Editable)', Resolved)")

        for item in items['issues']:
            sprintdescription = item['fields']['customfield_11200']

            sprintname = ""
            if sprintdescription:
                for sprint in sprintdescription:
                    sprintstate = sprint[sprint.find("state") + 6:sprint.find("name") - 1]
                    sprintname = sprint[sprint.find("name") + 5:sprint.find(",", sprint.find("name"))]

                    if sprintstate == "FUTURE":
                        break

            actionitem = {
                "key": item['key'],
                "summary": item['fields']['summary'],
                "storypoints": item['fields']['customfield_10003'],
                "labels": item['fields']['labels'],
                "sprint": sprintname
            }
            actionitems.append(actionitem)
    except:
        actionitems = []
        error = True

    # SUPPORT ITEMS #
    try:
        supports = jiraif.search(activeUser.get_session(), False,
                                 f"project=PVCSX AND type = Story AND labels = SUPPORT_ITEM AND labels = {teamlabel} AND "
                                 "status not in (Closed, 'Closed (Editable)', Resolved)")

        for support in supports['issues']:
            sprintdescription = support['fields']['customfield_11200']

            sprintname = ""
            if sprintdescription:
                for sprint in sprintdescription:
                    sprintstate = sprint[sprint.find("state") + 6:sprint.find("name") - 1]
                    sprintname = sprint[sprint.find("name") + 5:sprint.find(",", sprint.find("name"))]

                    if sprintstate == "FUTURE":
                        break

            supportitem = {
                "key": support['key'],
                "summary": support['fields']['summary'],
                "storypoints": support['fields']['customfield_10003'],
                "labels": support['fields']['labels'],
                "sprint": sprintname
            }
            supportitems.append(supportitem)
    except:
        supportitems = []
        error = True

    if not error:
        jsondata = {
            "data": {
                "features": safefeatures,
                "problems": problemreports,
                "actionitems": actionitems,
                "supportitems": supportitems
            }
        }

        retval = json.dumps(jsondata)
    else:
        retval = "NOK"

    return retval


@app.route('/api/savecapacity', methods=['POST'])
def saveCapacity():
    try:
        data = request.get_json()

        team = data["team"]
        year = data["year"]
        pi = data["pi"]

        with open(f"{team}_{year}_{pi}.json", "w") as file:
            json.dump(data, file)

        status = "ok"
    except Exception as err:
        status = f"NOK ({str(err)})"

    return status


@app.route('/api/loadcapacity', methods=['POST'])
def loadCapacity():
    try:
        dict = request.form.to_dict()

        team = dict["team"]
        year = dict["year"]
        pi = dict["pi"]

        with open(f"{team}_{year}_{pi}.json", "r") as file:
            data = json.load(file)

        status = data
    except Exception as err:
        status = {}

    return status


@app.route('/api/saveplan', methods=['POST'])
def savePlan():
    try:
        dict = request.form.to_dict()
        jsondata = json.loads(dict["data"])

        team = jsondata["team"]
        pi = jsondata["pi"]

        with open(f"{pi}-{team}.json", "w") as file:
            json.dump(jsondata["sprints"], file)

        status = "OK"
    except Exception as err:
        status = f"NOK ({str(err)})"

    return status


@app.route('/api/checkplan', methods=['GET'])
def checkPlan():
    try:
        pi = request.args.get("pi")

        status = glob.glob(f"{pi}*.json")
    except Exception as err:
        status = f"NOK ({str(err)})"

    return status


@app.route('/api/loadplan', methods=['GET'])
def loadPlan():
    try:
        pi = request.args.get("pi")
        year = request.args.get("year")
        team = request.args.get("team")

        with open(f"PI-{year}-{pi}-{team}.json", "r") as file:
            data = json.load(file)

        ret = data
    except Exception as err:
        ret = f"NOK ({str(err)}"

    return ret


@app.route('/api/loadplanandsprintissues', methods=['GET'])
def loadPlanAndSprintIssues():
    try:
        pi = request.args.get("pi")
        year = request.args.get("year")
        team = request.args.get("team")

        with open(f"{team}_{year}_PI{pi[-1]}.json", "r") as file:
            capacity = json.load(file)

        with open(f"PI-{year}-{pi}-{team}.json", "r") as file:
            plan = json.load(file)

        mysession = allUsers[session['username']].get_session()
        sprintids = jiraif.get_sprintidsofPI(mysession, f"R10-{team}-{year}-PI{pi[-1]}-")
        sprint1 = jiraif.get_allstoriesprsofsprint(mysession, sprintids['1'], True, True)
        sprint2 = jiraif.get_allstoriesprsofsprint(mysession, sprintids['2'], True, True)
        sprint3 = jiraif.get_allstoriesprsofsprint(mysession, sprintids['3'], True, True)
        sprintip = jiraif.get_allstoriesprsofsprint(mysession, sprintids['P'], True, True)

        ret = {
            "capacity": capacity,
            "plan": plan,
            "actual": {
                "sprint1": sprint1,
                "sprint2": sprint2,
                "sprint3": sprint3,
                "sprintip": sprintip
            }
        }

        if '4' in sprintids:
            sprint4 = jiraif.get_allstoriesprsofsprint(mysession, sprintids['4'], True, True)
            ret["actual"]["sprint4"] = sprint4

    except Exception as err:
        ret = f"NOK ({str(err)})"

    return ret


@app.route('/api/moveissuetosprint', methods=['POST'])
def moveIssueToSprint():
    try:
        dict = request.form.to_dict()
        key = dict['key']
        sprint = dict['sprint']

        status = jiraif.set_sprinttosprint(allUsers[session['username']].get_session(), key, sprint)
    except Exception as err:
        status = f"NOK ({str(err)})"

    return status


@app.route('/api/moveissuetobacklog', methods=['POST'])
def moveIssueToBacklog():
    try:
        dict = request.form.to_dict()
        key = dict['key']
        activeUser = allUsers[session['username']]

        status = jiraif.set_sprinttobacklog(activeUser.get_session(), key)
    except Exception as err:
        status = f"NOK ({str(err)})"

    return status


# Check JIRA connection
@app.route('/api/jira', methods=['GET'])
def checkjira():
    activeUser = allUsers[session['username']]

    try:
        result = jiraif.search(activeUser.get_session(), False,
                               "project=PVCSX AND labels='XVP-TEAM-AG' AND type = Story AND sprint='R10-AG-2022-PI3-2'")

        if (result['issues']):
            status = "OK"
    except:
        status = "NOK"

    return status


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True, ssl_context='adhoc')
