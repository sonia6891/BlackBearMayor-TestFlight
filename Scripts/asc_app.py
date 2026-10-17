"""App Store Connect chores with the same API key as the TestFlight upload (see asc_signing.py for the token).

register [name]: registers the Bundle ID when missing and says whether the app record exists yet.
rename <name>: sets the app's name on every editable App Information localization.
testflight [build]: waits for that build (default: the newest) to appear and finish processing, then makes sure every
internal TestFlight group has it. A just-uploaded build takes a few minutes to show up at all, so name it.

Environment: ASC_KEY_ID, ASC_ISSUER_ID, APP_BUNDLE_ID, RUNNER_TEMP (the key in $RUNNER_TEMP/asc-signing/AuthKey.p8).
"""
import os
import sys
import time
import urllib.parse

from asc_signing import ApiError, call


def app_id() -> str:
    bundle = os.environ["APP_BUNDLE_ID"]
    apps = [a for a in call("GET", "apps?filter[bundleId]=" + urllib.parse.quote(bundle))["data"] if a["attributes"]["bundleId"] == bundle]
    if not apps:
        raise ApiError(f"App Store Connect 沒有 Bundle ID 為 {bundle} 的 App。")
    print(f"App: {apps[0]['attributes']['name']} ({apps[0]['id']})")
    return apps[0]["id"]


def register(name: str) -> None:
    """Registers the Bundle ID if it is missing and reports whether the App Store Connect app record exists yet
    (the record itself can only be created in the App Store Connect website)."""
    bundle = os.environ["APP_BUNDLE_ID"]
    listed = call("GET", "bundleIds?limit=200&filter[identifier]=" + urllib.parse.quote(bundle))["data"]
    if any(item["attributes"]["identifier"] == bundle for item in listed):
        print(f"Bundle ID {bundle}: already registered.")
    else:
        call("POST", "bundleIds", {"data": {"type": "bundleIds", "attributes": {"identifier": bundle, "name": name, "platform": "IOS"}}})
        print(f"Bundle ID {bundle}: registered as {name}.")
    apps = [a for a in call("GET", "apps?filter[bundleId]=" + urllib.parse.quote(bundle))["data"] if a["attributes"]["bundleId"] == bundle]
    if apps:
        print(f"App record {apps[0]['attributes']['name']} ({apps[0]['id']}) exists: builds can be uploaded to TestFlight.")
    else:
        print(f"::warning::App Store Connect 還沒有 Bundle ID 為 {bundle} 的 App 紀錄：請到 App Store Connect 新增 App 並選這個 Bundle ID，再執行上傳。")


def status() -> None:
    """Lists the app's latest builds and its TestFlight groups with tester and build counts (counts only: logs are public)."""
    app = app_id()
    for build in call("GET", f"builds?filter[app]={app}&sort=-uploadedDate&limit=5")["data"]:
        a = build["attributes"]
        print(f"Build {a['version']}: processing {a['processingState']}, expired {a.get('expired')}, uploaded {a.get('uploadedDate')}")
    groups = call("GET", f"betaGroups?filter[app]={app}&limit=50")["data"]
    if not groups:
        print("TestFlight groups: none")
    for group in groups:
        g = group["attributes"]
        testers = call("GET", f"betaGroups/{group['id']}/betaTesters?limit=200")["data"]
        builds = call("GET", f"betaGroups/{group['id']}/builds?limit=50")["data"]
        print(f"Group: internal {g.get('isInternalGroup')}, all builds {g.get('hasAccessToAllBuilds')}, testers {len(testers)}, builds {len(builds)}")


def rename(name: str) -> None:
    app = app_id()
    changed = 0
    for info in call("GET", f"apps/{app}/appInfos")["data"]:
        state = info["attributes"].get("state") or info["attributes"].get("appStoreState")
        for loc in call("GET", f"appInfos/{info['id']}/appInfoLocalizations")["data"]:
            old = loc["attributes"].get("name")
            if old == name:
                print(f"{loc['attributes']['locale']} ({state}): already {name}")
                continue
            try:
                call("PATCH", f"appInfoLocalizations/{loc['id']}", {"data": {"type": "appInfoLocalizations", "id": loc["id"], "attributes": {"name": name}}})
                print(f"{loc['attributes']['locale']} ({state}): {old} -> {name}")
                changed += 1
            except ApiError as error:
                print(f"::warning::{loc['attributes']['locale']} ({state}) not changed: {error}")
    print(f"Renamed {changed} localization(s).")


def testflight(version: str = "") -> None:
    app = app_id()
    deadline = time.time() + 45 * 60
    while True:
        query = f"builds?filter[app]={app}&sort=-uploadedDate&limit=1" + (f"&filter[version]={urllib.parse.quote(version)}" if version else "")
        builds = call("GET", query)["data"]
        if not builds:
            if version and time.time() < deadline:
                print(f"Build {version}: not listed yet")
                time.sleep(60)
                continue
            raise ApiError(f"找不到組建 {version or ''}。".replace(" 。", "。"))
        build = builds[0]
        state = build["attributes"]["processingState"]
        print(f"Build {build['attributes']['version']}: {state}")
        if state == "VALID":
            break
        if state in ("FAILED", "INVALID"):
            raise ApiError(f"組建 {build['attributes']['version']} 處理失敗（{state}），請查看 App Store Connect 的電子郵件。")
        if time.time() > deadline:
            raise ApiError("等了 45 分鐘組建仍在處理中，請稍後在 TestFlight 查看。")
        time.sleep(60)
    for group in call("GET", f"betaGroups?filter[app]={app}&limit=50")["data"]:
        attrs = group["attributes"]
        if not attrs.get("isInternalGroup"):
            continue
        if attrs.get("hasAccessToAllBuilds"):
            print(f"Internal group {attrs['name']}: gets every build automatically.")
            continue
        call("POST", f"betaGroups/{group['id']}/relationships/builds", {"data": [{"type": "builds", "id": build["id"]}]})
        print(f"Internal group {attrs['name']}: build {build['attributes']['version']} added.")
    print(f"Build {build['attributes']['version']} is ready in TestFlight.")


if __name__ == "__main__":
    try:
        if sys.argv[1] == "status":
            status()
        elif sys.argv[1] == "register":
            register(sys.argv[2] if len(sys.argv) > 2 else "BlackBearMayor")
        elif sys.argv[1] == "rename":
            rename(sys.argv[2])
        elif sys.argv[1] == "testflight":
            testflight(sys.argv[2] if len(sys.argv) > 2 else "")
        else:
            raise SystemExit("usage: asc_app.py register [name] | rename <name> | testflight [build]")
    except ApiError as error:
        print(f"::error::{error}")
        sys.exit(1)
