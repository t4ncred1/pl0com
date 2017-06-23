#include <stdio.h>


extern void __pl0_start(void);


void __print(int param)
{
  printf("%d\n", param);
}


int __read(void)
{
  int tmp;
  scanf("%d", &tmp);
  return tmp;
}


int main(int argc, char *argv[])
{
  __pl0_start();
}



