# Network Coding as a Forward Error Correction Technique on Unreliable Links Description

This thesis explores network coding as a Forward Error Correction (FEC) technique, specifically known as systematic block-based Random Linear Network Coding (RLNC). This technique protects the original information from data losses by using redundant information. The study focuses on the impact of the placement and quantity of this redundant information, examining various combinations and their performance under different transmission conditions.

# Technologies and Tools

Programming Language: Python
Library: PyErasure (for data encoding and decoding)

# Installation Instructions
To install the PyErasure library, click on the following link:
    https://pyerasure.pages.dev/1.3.0/

# Usage Instructions
To run the program, follow these steps:

1) Open the terminal and execute the command:
   python3 program_name seed
   Replace program_name with the name of your program file and seed with a number of your choice.

2) Enter the total number of symbols to be sent.

3)Select the number of symbols that will be grouped together (generation size).

4)Set the packet loss probability.

5)Choose the ratio of encoded packets to source packets being sent.

6) Selection of Packet Management Mechanisms: Choose between  drop out-of-order packet and drop generation. (For more information, refer to Kiose-thesis)
