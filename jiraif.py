import json


class JiraError(Exception):
    pass


def search(session, certfile, jql, limit=1000):
    request = {
        "jql": jql,
        "maxResults": limit
    }

    r = session.post("https://jira.frequentis.frq/rest/api/2/search", json=request, verify=certfile)
    if r.status_code != 200:
        raise JiraError("HTTP Error %s" % r.status_code)
    return r.json()


def get_allsprints(session, closed=False, active=True, future=True):
    islast = False
    startat = 0
    sprintarray = []

    while islast is False:
        r = session.get(f"https://jira.frequentis.frq/rest/agile/1.0/board/11880/sprint?startAt={startat}",
                        verify=False)

        sprints = r.json()
        islast = sprints["isLast"]
        startat += sprints["maxResults"]

        for sprint in sprints["values"]:
            if (closed is True and sprint['state'] == 'closed') \
                    or (active is True and sprint['state'] == 'active') \
                    or (future is True and sprint['state'] == 'future'):
                sprintarray.insert(0, sprint)

    return sprintarray


def get_allstoriesprsofsprint(session, sprintval, resolved=False, closed=False):
    islast = False
    startat = 0
    issuedict = {}

    while islast is False:
        r = session.get("https://jira.frequentis.frq/rest/agile/1.0/sprint/{sprint}/issue?startAt={startat}".
                        format(sprint=sprintval, startat=startat), verify=False)

        issues = r.json()
        if issues["startAt"] + issues["maxResults"] > issues["total"]:
            islast = True
        else:
            startat += issues["maxResults"]

        for rawissue in issues["issues"]:
            if (rawissue["fields"]["status"]["name"] != "Resolved" or resolved) and \
                    (rawissue["fields"]["status"]["name"] != "Closed" or closed) and \
                    rawissue["fields"]["issuetype"]["name"] != "Sub-task":

                points = 0 if not rawissue["fields"]["customfield_10003"] else rawissue["fields"]["customfield_10003"]
                issuedict[rawissue["key"]] = {
                    "summary": rawissue["fields"]["summary"],
                    "type": rawissue["fields"]["issuetype"]["name"],
                    "status": rawissue["fields"]["status"]["name"],
                    "subtasks": rawissue["fields"]["subtasks"],
                    "sprints": rawissue["fields"]["closedSprints"] if "closedSprints" in rawissue["fields"] else "",
                    "labels": rawissue["fields"]["labels"],
                    "points": points
                }

    return issuedict


def add_fixversion(session, key, version):
    body = {
        "update": {
            "fixVersions": [
                {
                    "add": {
                        "name": version
                    }
                }
            ]
        }
    }

    r = session.put("https://jira.frequentis.frq/rest/api/2/issue/{key}".
                        format(key=key), json=body, verify=False)

    return r.status_code

def del_fixversion(session, key, version):
    body = {
        "update": {
            "fixVersions": [
                {
                    "remove": {
                        "name": version
                    }
                }
            ]
        }
    }

    r = session.put("https://jira.frequentis.frq/rest/api/2/issue/{key}".
                        format(key=key), json=body, verify=False)

    return r.status_code


def upd_fixversion(session, key, addversion, remversion):
    body = {
        "update": {
            "fixVersions": [
                {
                    "remove": {
                        "name": remversion
                    }
                },
                {
                    "add": {
                        "name": addversion
                    }
                }
            ]
        }
    }

    r = session.put("https://jira.frequentis.frq/rest/api/2/issue/{key}".
                        format(key=key), json=body, verify=False)

    return r.status_code


def get_sprintid(session, sprintname):
    sprintid = 0
    islast = False
    startat = 0

    while islast is False:
        r = session.get(f"https://jira.frequentis.frq/rest/agile/1.0/board/11880/sprint?startAt={startat}",
                        verify=False)
        sprints = r.json()

        islast = sprints["isLast"]
        startat = sprints["startAt"] + sprints["maxResults"]

        for sprint in sprints["values"]:
            if sprint["name"] == sprintname:
                sprintid = sprint["id"]
                islast = True
                break

    return sprintid


def get_sprintidsofPI(session, prefix):
    sprintids = {}
    islast = False
    startat = 0

    while islast is False:
        r = session.get(f"https://jira.frequentis.frq/rest/agile/1.0/board/11880/sprint?startAt={startat}",
                        verify=False)
        sprints = r.json()

        islast = sprints["isLast"]
        startat = sprints["startAt"] + sprints["maxResults"]

        for sprint in sprints["values"]:
            if prefix in sprint["name"]:
                sprintids[sprint["name"][-1]] = sprint["id"]

    return sprintids


def set_sprinttosprint(session, key, sprintname):
    sprintid = get_sprintid(session, sprintname)

    r = session.post("https://jira.frequentis.frq/rest/agile/1.0/sprint/{sprintid}/issue".format(sprintid=sprintid),
                     data=json.dumps({"issues": [key]}),
                     headers={"Content-Type": "application/json"}, verify=False)

    return json.dumps(r.status_code)


def set_sprinttobacklog(session, key):
    r = session.post("https://jira.frequentis.frq/rest/agile/1.0/backlog/issue",
                     data=json.dumps({"issues": [key]}),
                     headers={"Content-Type": "application/json"}, verify=False)

    return json.dumps(r.status_code)
