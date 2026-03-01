#include <X11/Xlib.h>
#include <X11/extensions/XInput2.h>
#include <X11/extensions/XTest.h>
#include <X11/keysym.h>
#include <X11/XKBlib.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <math.h>

typedef struct {
    int key_count;
    double mouse_distance;
    int left_click_count;
    int right_click_count;
    double scroll_amount; // total scroll steps (direction-agnostic)
    int enter_key_count;
    int last_mouse_x;
    int last_mouse_y;
} ActivityData;

static ActivityData activity = {0, 0.0, 0, 0, 0.0, 0, -1, -1};
static Display* display = NULL;
static int xi_opcode;

// Initialize X11 and XInput2
int init_tracking() {
    display = XOpenDisplay(NULL);
    if (!display) {
        return 0;
    }

    // Check for XInput2
    int event, error;
    if (!XQueryExtension(display, "XInputExtension", &xi_opcode, &event, &error)) {
        return 0;
    }

    // Check XInput2 version
    int major = 2, minor = 0;
    if (XIQueryVersion(display, &major, &minor) != Success) {
        return 0;
    }

    // Select events for all devices
    Window root = DefaultRootWindow(display);
    
    XIEventMask eventmask;
    unsigned char mask[XIMaskLen(XI_RawMotion)] = {0};

    // Key presses, mouse motion, button presses
    XISetMask(mask, XI_RawKeyPress);
    XISetMask(mask, XI_RawMotion);
    XISetMask(mask, XI_RawButtonPress);
    
    eventmask.deviceid = XIAllMasterDevices;
    eventmask.mask_len = sizeof(mask);
    eventmask.mask = mask;
    
    XISelectEvents(display, root, &eventmask, 1);
    XSync(display, False);

    return 1;
}

// Process events
void process_events() {
    if (!display) return;

    while (XPending(display)) {
        XEvent ev;
        XNextEvent(display, &ev);

        if (ev.xcookie.type == GenericEvent && 
            ev.xcookie.extension == xi_opcode &&
            XGetEventData(display, &ev.xcookie)) {
            
            XIRawEvent* raw_event = (XIRawEvent*)ev.xcookie.data;

            switch (ev.xcookie.evtype) {
                case XI_RawKeyPress:
                    activity.key_count++;
                    {
                        int keycode = raw_event->detail;
                        // Translate keycode to keysym (try level 0 & 1)
                        KeySym ks = 0;
                        for (int lvl = 0; lvl < 2 && ks == 0; lvl++) {
                            ks = XkbKeycodeToKeysym(display, keycode, 0, lvl);
                        }
                        if (ks == XK_Return || ks == XK_KP_Enter) {
                            activity.enter_key_count++;
                        }
                        // Fallback heuristic: common keycodes for Enter on X11 (US layouts: 36)
                        if (ks == 0 && (keycode == 36 || keycode == 104)) { // 104 often KP_Enter
                            activity.enter_key_count++;
                        }
                    }
                    break;

                case XI_RawMotion: {
                    double dx = 0.0, dy = 0.0;
                    
                    // Get raw motion values
                    double* raw_values = raw_event->raw_values;
                    unsigned char* valuators = raw_event->valuators.mask;
                    int nvalues = 0;
                    
                    for (int i = 0; i < raw_event->valuators.mask_len * 8; i++) {
                        if (XIMaskIsSet(valuators, i)) {
                            if (i == 0) dx = raw_values[nvalues];
                            if (i == 1) dy = raw_values[nvalues];
                            nvalues++;
                        }
                    }
                    
                    // Calculate distance moved
                    double distance = sqrt(dx * dx + dy * dy);
                    activity.mouse_distance += distance;
                    break;
                }
                break;
                case XI_RawButtonPress: {
                    // Button detail values: 1 left, 2 middle, 3 right, 4 scroll up, 5 scroll down
                    int button = raw_event->detail;
                    if (button == 1) {
                        activity.left_click_count++;
                    } else if (button == 3) {
                        activity.right_click_count++;
                    } else if (button == 4) {
                        // Scroll up (count absolute step)
                        activity.scroll_amount += 1.0;
                    } else if (button == 5) {
                        // Scroll down (count absolute step)
                        activity.scroll_amount += 1.0;
                    }
                }
                break;
            }

            XFreeEventData(display, &ev.xcookie);
        }
    }
}

// Get current activity data
void get_activity_data(int* key_count, double* mouse_distance) {
    *key_count = activity.key_count;
    *mouse_distance = activity.mouse_distance;
}

// Extended data accessor
void get_extended_activity_data(int* key_count, double* mouse_distance, int* left_clicks, int* right_clicks, double* scroll_amount, int* enter_count) {
    *key_count = activity.key_count;
    *mouse_distance = activity.mouse_distance;
    *left_clicks = activity.left_click_count;
    *right_clicks = activity.right_click_count;
    *scroll_amount = activity.scroll_amount;
    *enter_count = activity.enter_key_count;
}

// Reset activity counters
void reset_activity() {
    activity.key_count = 0;
    activity.mouse_distance = 0.0;
    activity.left_click_count = 0;
    activity.right_click_count = 0;
    activity.scroll_amount = 0.0;
    activity.enter_key_count = 0;
}

// Cleanup
void cleanup_tracking() {
    if (display) {
        XCloseDisplay(display);
        display = NULL;
    }
}
