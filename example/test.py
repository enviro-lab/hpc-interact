#!/usr/bin/env python3

from hpc_interact import Scripter

# do some sftp stuff
scripter = Scripter(config="~/.pooPatrol/hpc_config.txt", site='hpc.uncc.edu', mode='sftp')
scripter.add_step("### Making a test dir/file...")
scripter.add_step("! mkdir -p test_dir")
scripter.add_step("! echo 'some text' > test_dir/test_file.txt")
# scripter.add_step("! echo 'some text' > test_dir/test_file2.txt")
scripter.add_step("### Transferring the test dir/file to hpc...")
scripter.put("test_dir/*")
scripter.add_step("### Transferring it back to a new directory...")
scripter.get("test_dir/*",outdir="test_dir2")
scripter.preview_steps()
scripter.run()

# # show off what we did
# import os
# print()
# print("### Here's the local file we just made:")
# print(os.listdir("test_dir"))
# print()
# print("SSH-ing into hpc...\n")

# # Look at things on the hpc
# scripter.reset_mode("ssh")
# scripter.add_step('')
# scripter.add_step('### Listing hpc test* files/directories')
# scripter.ls('test*')
# scripter.run()
