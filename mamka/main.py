from Foundation import NSObject, NSAppleScript, NSTimer
from AppKit import NSApplication, NSApp, NSWorkspace
from Cocoa import NSEvent, NSKeyDownMask
from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionOnScreenOnly, kCGNullWindowID
from PyObjCTools import AppHelper

from Quartz.CoreGraphics import CGEventSourceSecondsSinceLastEventType, kCGEventSourceStateHIDSystemState, kCGAnyInputEventType

import time
import os
import json


def get_time_ms():
    return time.time_ns() // 1000000


class AppDelegate(NSObject):
    # def applicationDidFinishLaunching_(self, note):
    #     NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
    #         NSKeyDownMask, self.handler.on_key_down)
    #     NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
    #         NSKeyDownMask, self.handler.on_key_down)

    def applicationActivated_(self, note):
        app = note.userInfo().objectForKey_('NSWorkspaceApplicationKey')
        self.handler.on_app_activated(app)

    def screenSleep_(self, note):
        self.handler.on_sleep()

    def writeActiveApp_(self, timer):
        self.handler.on_update()


class GoogleChrome:
    def __init__(self):
        self.chrome_tab_script = NSAppleScript.alloc().initWithSource_(
            """
            tell application "Google Chrome"
                get URL of active tab of first window
            end tell
            """
        )

    def get_current_tab(self):
        res = self.chrome_tab_script.executeAndReturnError_(None)
        if res[0] is None:
            return None

        return str(res[0].stringValue())


class Spotify:
    def __init__(self):
        self.src = """
        tell application "Spotify"
            set myTrack to name of current track
            set myArtist to artist of current track
            set myAlbum to album of current track
            set info to ""
            if player state as text is equal to "playing"
                set info to myArtist & " – " & myTrack & " – " & myAlbum
            end if
	    end tell
	    return info"""
        self.script = NSAppleScript.alloc().initWithSource_(self.src)

    def get_data(self):
        res = self.script.executeAndReturnError_(None)
        if res[0] is None:
            return None
        res = str(res[0].stringValue())
        if len(res) == 0:
            return None
        return res


def get_current_window_name(app_name):
    if app_name is None:
        return None
    options = kCGWindowListOptionOnScreenOnly
    window_list = CGWindowListCopyWindowInfo(options, kCGNullWindowID)
    for window in window_list:
        try:
            if window['kCGWindowOwnerName'] == app_name:
                window_name = window['kCGWindowName']
                return window_name
        except KeyError:
            pass
    return None


def get_foremost_app():
    ws = NSWorkspace.sharedWorkspace()
    app = ws.frontmostApplication()
    return app.localizedName()


def seconds_since_last_input() -> float:
    return CGEventSourceSecondsSinceLastEventType(
        kCGEventSourceStateHIDSystemState,
        kCGAnyInputEventType
    )


class Handler:
    def __init__(self):
        self.google_chrome = GoogleChrome()
        self.spotify = Spotify()

        self.state = {'app_name': get_foremost_app()}

    # def on_key_down(self, event):
    #     # print(event)
    #     # TODO: use it to measure AFK
    #     # TODO: add mouse activity
    #     pass

    def on_sleep(self) -> None:
        self.state = {
            'app_name': '__LOCKEDSCREEN'
        }

    def on_app_activated(self, app) -> None:
        app_name = app.localizedName()
        self.state = {
            'app_name': app_name
        }
        if app_name == "Google Chrome":
            self.state['tab'] = self.google_chrome.get_current_tab()

    def on_update(self) -> None:
        app_name = self.state['app_name']
        if app_name != '__LOCKEDSCREEN':
            win_name = get_current_window_name(app_name)
            self.state['win_name'] = win_name
        self.state['music'] = self.spotify.get_data()
        self.state['time'] = get_time_ms()
        self.state['last_input_delta'] = seconds_since_last_input()
        print(f"Tick: {self.state}")
        with open("log.txt", 'a') as fd:
            log_entry = json.dumps(self.state)
            fd.write(log_entry + '\n')


class EventSniffer:
    def __init__(self, polling_time: float = 1) -> None:
        self.polling_time = polling_time  # in seconds

    def run(self) -> None:
        NSApplication.sharedApplication()
        self.delegate = AppDelegate.alloc().init()
        self.delegate.handler = Handler()

        NSApp().setDelegate_(self.delegate)

        self.workspace = NSWorkspace.sharedWorkspace()
        nc = self.workspace.notificationCenter()

        nc.addObserver_selector_name_object_(
            self.delegate,
            'applicationActivated:',
            'NSWorkspaceDidActivateApplicationNotification',
            None,
        )

        nc.addObserver_selector_name_object_(
            self.delegate,
            'screenSleep:',
            'NSWorkspaceScreensDidSleepNotification',
            None,
        )

        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            self.polling_time, self.delegate, 'writeActiveApp:', None, True)

        AppHelper.runConsoleEventLoop(maxTimeout=1)


def main():
    # TODO: check if it's already exist?
    pid = str(os.getpid())
    with open("mamka_pid", 'w') as f:
        f.write(pid)

    print(f"Running app. PID = {pid}")

    app = EventSniffer()
    app.run()


if __name__ == "__main__":
    main()
