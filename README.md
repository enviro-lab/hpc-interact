# hpc-interact
Used for scripting file transfer (sftp) and sending commands (ssh) to hpc - a wrapper for `expect`

## Requires `expect`
If needed, install via:
```
$ sudo apt install expect
```

## Install
From PyPI:
```console
pip install hpc-interact
```

Or just clone the repo and use `hpc_interact.py` directly.

## Usage
Instantiate a Scripter object:
```python
>>> # Connect via sftp
>>> from hpc_interact import Scripter
>>> scripter = Scripter(config="./login_config", site='somewhere.uni.edu', mode='sftp')
>>> # NOTE: If "./login_config" doesn't exist, you'll be prompted to create it
```

Prepare any steps to undertake
```python
>>> outdir = "/Users/me/somedir"
>>> scripter.cwd("/some/remote/directory")
>>> for file in ["file1.txt","file2.txt"]:
...     scripter.get(file,outdir)
```

### To see what steps you've added, run:
```
>>> scripter.preview_steps()
```
Output:
```console

Command preview:
(0, 'cd /some/remote/directory\n')
(1, 'mkdir /Users/me/somedir\n')
(2, 'cd /Users/me/somedir\n')
(3, 'put file1.txt \n\n')
(4, 'mkdir /Users/me/somedir\n')
(5, 'cd /Users/me/somedir\n')
(6, 'put file2.txt \n\n')
```

### To run:
```python
>>> scripter.run()
```

### Forgot something but don't want to create a new Scripter object?
```python
>>> scripter.clear()
>>> scripter.put("/Users/me/another-dir/cool_script.sh",outdir="/some/remote/directory",new_name="coolest_script_on_the_hpc.sh")
>>> scripter.run()
```

### Run a script on the cluster
```python
>>> # Connect via ssh
>>> from hpc_interact import cluster.Scripter
>>> scripter = Scripter(config="./login_config", site='somewhere.uni.edu', mode='ssh')
>>> 
>>> # run it
>>> scripter.basic_step("bash","/some/remote/directory/coolest_script_on_the_hpc.sh")
>>> scripter.run()
```

### Started as ssh but want need to transfer files?
```python
>>> scripter.reset_mode("sftp")
>>> add_some_steps(scripter)
>>> scripter.run()
```