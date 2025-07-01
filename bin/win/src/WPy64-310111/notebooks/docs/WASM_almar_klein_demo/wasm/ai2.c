#include <stdlib.h>
#include <math.h>

/* Imports */
void toggle_shoot(int b);
void toggle_turn_left(int b);
void toggle_turn_right(int b);
float Math_atan(float v);
//void debug(float a, float b);

const float pi = 3.14159265358979;

float playerX = 0.0;
float playerY = 0.0;
float playerA = 0.0;

float nearestEnemyX = 0.0;
float nearestEnemyY = 0.0;
float nearestEnemyD = 99999999999999999.0;

void clear_screen() { // reset nearest enemy
  nearestEnemyX = 0.0;
  nearestEnemyY = 0.0;
  nearestEnemyD = 99999999999999999.0;
}

void draw_player(float x, float y, float a) {
  playerX = x;
  playerY = y;
  while (a > 2*pi)  a -= 2*pi;
  while (a < 0)  a += 2*pi2;
  playerA = a;
}

void draw_enemy(float x, float y) {
  float d = (x - playerX) * (x - playerX) + (y - playerY) * (y - playerY);
  if (d < nearestEnemyD) {
    nearestEnemyX = x;
    nearestEnemyY = y;
    nearestEnemyD = d;
  }
}

void update() {
  float enemyA = Math_atan((nearestEnemyY - playerY) / (nearestEnemyX - playerX));
  
  float a = enemyA - playerA;
  while (a > +pi)  a -= 2*pi;
  while (a < -pi)  a += 2*pi;
  
  if (fabsf(a) < 1.0) {
    toggle_shoot(1);
  } else {
    toggle_shoot(0);
  }
  
  if (a > 0.0) {
    toggle_turn_left(0); toggle_turn_right(1);
  } else {
    toggle_turn_left(1); toggle_turn_right(0);
  }
}
