from Foundation import NSObject, NSAppleScript, NSTimer
from AppKit import NSApplication, NSApp, NSWorkspace
from Cocoa import NSEvent, NSKeyDownMask
from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionOnScreenOnly, kCGNullWindowID
from PyObjCTools import AppHelper

class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, note):
        NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(NSKeyDownMask, self.handler.on_key_down)
        NSEvent.addLocalMonitorForEventsMatchingMask_handler_(NSKeyDownMask, self.handler.on_key_down)

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
                    print(window)
                    window_name = window['kCGWindowName']
                    return window_name
            except KeyError:
                pass
        return None

class Handler:
    def __init__(self):
        self.google_chrome = GoogleChrome()
        self.spotify = Spotify()

        self.workspace = NSWorkspace.sharedWorkspace()
        self.current_app = {'name': None}

    def on_key_down(self, event):
        # print(event)
        # TODO: use it to measure AFK
        # TODO: add mouse activity
        pass

    def on_sleep(self):
        self.current_app = {
            'name': '__LOCKEDSCREEN'
        }

    def on_app_activated(self, app):
        app_name = app.localizedName()
        self.current_app = {
            'name': app_name
        }
        if app_name == "Google Chrome":
            self.current_app['tab'] = self.google_chrome.get_current_tab()
        print(f"activated {self.current_app}")

    def on_update(self):
        app_name = self.current_app['name']
        if app_name == '__LOCKEDSCREEN':
            return

        win_name = get_current_window_name(app_name)
        self.current_app['win_name'] = win_name
        music_data = self.spotify.get_data()
        print(f"Tick: {self.current_app}. {music_data}")

class EventSniffer:
    def __init__(self):
        self.polling_time = 1 # in seconds

    def run(self):
        print("Running app")
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

        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(self.polling_time, self.delegate, 'writeActiveApp:', None, True)

        AppHelper.runConsoleEventLoop(maxTimeout=1)

def main():
    app = EventSniffer()
    app.run()

if __name__ == "__main__":
    main()
