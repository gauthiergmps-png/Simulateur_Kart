# a="abc"
# print (a[2])
# class A:
#     def __init__(self, a):
#         self.a = a
#     def __str__(self):
#         return f"A({self.a})"
    
#     def b(self):
#         return 2*self.a
#     def c(self):
#         return b()
# a = A(1)
# print (a.c())
import numpy as np

a=[]
print(a, type(a))
a+= [2]
print(a, type(a))
b= [1., 2.]
a+= b
print(a, type(a))


