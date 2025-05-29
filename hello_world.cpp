#include <iostream>
// includes the standard input-output stream library in C++

int main() {
    // std::cout: This is the standard character output stream in C++.
    // <<: This is the stream insertion operator. It is used to send data to the output stream.
    std::cout << "Hello, World!" << std::endl;
    // << std::endl;: This inserts a newline character and flushes the output buffer, ensuring that the text is displayed immediately.
    return 0;
}

// complie and run the program
// make hello_world
// ./hello_world
// or
// $ g++ hello_world.cpp -o hello_world