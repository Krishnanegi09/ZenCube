#include <stdio.h>
#include <string.h>
void secret()
{
    printf(" Buffer Overflow Succeeded! You've entered the secret function!\n");
}
void vulnerable()
{
    char buffer[20];
    printf("Enter some text:\n");
    gets(buffer);
    printf("You entered: %s\n", buffer);
    // Unsafe function that doesn't check bounds!
}
int main()
{
    vulnerable();
    printf("Program finished normally.\n");
    return 0;
}