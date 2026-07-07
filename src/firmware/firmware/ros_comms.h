#ifndef ROS_COMMS_H
#define ROS_COMMS_H

#include <Arduino.h>

void init_ros_comms();
void spin_ros_comms();
void spin_ros_some();
void publish_ros_feedback();

#endif // ROS_COMMS_H
