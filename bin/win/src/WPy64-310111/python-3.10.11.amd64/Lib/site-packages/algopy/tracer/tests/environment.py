"""
define environmental settings for the test files

""" 

import os
class Settings:
    output_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)) , 'test_output')
