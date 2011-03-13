#include <stdio.h>

static void process(FILE *f)
{
  int c;
  while ( (c=getc(f)) != EOF ) {
    if (c=='\'' || c=='"') {           /* literal */
      int q=c;
      do {
        putchar(c);
        if (c=='\\') putchar(getc(f));
        c=getc(f);
      } while (c!=q);
      putchar(c);
    }
    else if (c=='/') {             /* opening comment ? */
      c=getc(f);
      if (c!='*') {                 /* no, recover */
        putchar('/');
        ungetc(c,f);
      } else {
        int p;
        putchar(' ');               /* replace comment with space */
        do {
          p=c;
          c=getc(f);
          if (c == '*') {
            c=getc(f);
            if (c == '/')
              break;
            else
              ungetc(c,f);
          }
        } while (c!='/' || p!='*');
      }
    }
    else {
      putchar(c);
    }
  }
}

int main(int argc, char *argv[])
{
  process(stdin);
  return 0;
}
