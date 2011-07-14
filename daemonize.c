#include <stdlib.h>
#include <unistd.h>

int main(int argc, char *argv[], char *envp[])
{
  int i=fork();
  if (i<0) exit(1); /* fork error */
  if (i>0) exit(0); /* parent exits */
  /* child (daemon) continues */
  return execve(argv[1], &argv[1], envp);
}
