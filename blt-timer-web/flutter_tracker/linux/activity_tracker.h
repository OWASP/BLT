#ifndef ACTIVITY_TRACKER_H
#define ACTIVITY_TRACKER_H

#ifdef __cplusplus
extern "C" {
#endif

int init_tracking();
void process_events();
void get_activity_data(int* key_count, double* mouse_distance);
void get_extended_activity_data(int* key_count, double* mouse_distance, int* left_clicks, int* right_clicks, double* scroll_amount);
void reset_activity();
void cleanup_tracking();

#ifdef __cplusplus
}
#endif

#endif // ACTIVITY_TRACKER_H
