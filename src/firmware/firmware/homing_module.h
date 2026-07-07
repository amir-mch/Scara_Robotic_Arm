#ifndef HOMING_MODULE_H
#define HOMING_MODULE_H

#include <Arduino.h>

extern volatile bool homing_requested;

void initHomingSystem();
void runHomingSequence();

#endif // HOMING_MODULE_H
