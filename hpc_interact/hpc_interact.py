#!/usr/bin/env python3

import os
from pathlib import Path
from typing import List
from getpass import getpass

def fix_quote(string):
    """Returns `string` with double quotes converted (" -> \")"""
    return str(string).replace('"','\\"')

class Step:
    """A class to hold the expect and send commands that will be fed to `expect` on the command line

    Arguments:
        expect (str): the prompt to expect before acting
        cmd (str): the command to send
        mode (str, optional): how to connect to the host (options: [sftp, ssh]). Defaults to "sftp".
        quote (str, optional): The quotation symbol to use (in case the other one is part of the string). Defaults to '"'.
    """

    def __init__(self,expect,cmd,input_quote='"',expect_quote='"') -> None:
        """Creates a step to use with `expect` 

        Args:
            expect (str): the prompt to expect before acting
            cmd (str): the command to send
            mode (str, optional): how to connect to the host (options: [sftp, ssh]). Defaults to "sftp".
            quote (str, optional): The quote symbol to use (in case the other one is part of the string). Defaults to '"'. Not fully employed everywhere. Single quotes ensure no interpolation of the command.
        """

        self.expectation = f'expect "{fix_quote(expect)}"'
        self.action = f'send -- "{fix_quote(cmd)}\n"'

    def __repr__(self,sep="\n") -> str:
        """Prints the Step with the expect statement and action seperated by `sep`
        
        Args:
            sep (str): string by which to seperate each statement
        """

        action_fixed_quotes = self.action #.replace('"','\\"')
        return f"{self.expectation}{sep}{action_fixed_quotes}{sep}"

class Scripter:
    """A class to connect to an hpc cluster via sftp or ssh all wrapped up in a scripted batch of expect statements.

    * This class allows the user to run a series of prescribed commands 
            over ssh or sftp.
        * There is no error catching or acknowledgement from this script, as it
            is just a tool for scripting a set of commands to run all at once.
        * If commands are input incorrectly, read terminal output manually to 
            know which commands need to be corrected by the scripter.

    Arguments:
        username (str, optional): Your username. Defaults to None.
        password (str, optional): Your password. Defaults to None.
        site (str, optional): The hpc cluster to reach. Defaults to None.
        mode (str, optional): How you'd like to connect. Options: (sftp, ssh). Defaults to "sftp".
        group (str | int, optional): Group name to use if setting permissions. Defaults to None.
        config (str | Path, optional): Path to config file with credentials. Defaults to Path('~/hpc_config.txt').
        site_type (str, optional): What you'll be interacting with: [hpc, ncbi]. Defaults to "hpc".
    """

    def __init__(self,username=None,password=None,site=None,mode="sftp",group=None,config=None,site_type="hpc"):
        """Creates a Scripter instance

        Args:
            username (str, optional): Your username. Defaults to None.
            password (str, optional): Your password. Defaults to None.
            site (str, optional): The hpc cluster to reach. Defaults to None.
            mode (str, optional): How you'd like to connect. Options: (sftp, ssh). Defaults to "sftp".
            group (str | int, optional): Group name to use if setting permissions. Defaults to None.
            config (str | Path, optional): Path to config file with credentials. Defaults to Path('~/hpc_config.txt').
            site_type (str, optional): What you'll be interacting with: [hpc, ncbi]. Defaults to "hpc".

        Returns:
            Scripter: an object that builds an expect command for automating:
            * hpc cluster login, data transfer, and commands via ssh/sftp or 
            * ncbi data upload/download (future application - not yet implemented)
        """

        self.username = username
        self.__password = password
        self.group = group
        self.site = site
        if config:
            self.config=Path(config)
        else: self.config=None
        self.get_credentials(save=True,overwrite=False)
        self.actions:List[Step] = []
        self.__pw_steps = [
            Step(expect="Password:", cmd=self.__password),
            Step(expect="Passcode or option (1-3):", cmd=1)]
        self.mode, self.expect, self.entry = self.reset_mode(mode)
        self.open = f"expect << !\nset timeout -1\nspawn "
        self.close = "expect eof\n!\n"

    def reset_mode(self,mode,clear=True):
        """Resets mode attributes (mode, expect, entry), and clears any actions.

        Args:
            mode (str): How you'd like to connect. Options: (sftp, ssh).
            clear (bool): A flag to clear any steps already added. Defaults to True.
        """

        if clear and self.actions:
            self.clear()
        self.mode = mode
        if self.mode=="sftp":
            self.expect = "sftp>"
        else: # if self.mode=="ssh":
            self.expect = self.username
        self.entry = f"{self.mode} {self.username}@{self.site}\n"
        return self.mode, self.expect, self.entry

    def add_step(self,cmd,expect=None,input_quote='"',expect_quote='"'):
        """Adds a command to be run on the command line
        
        Args:
            cmd (str): the exact command to run
            expect (str, optional): the command prompt to wait for before acting. Default determined by mode.
            quote (str, optional): The quote symbol to use (in case the other one is part of the string). Defaults to '"'. Not fully employed everywhere. Single quotes ensure no interpolation of the command.
        """

        if not expect: expect = self.expect
        step = Step(cmd=cmd,expect=expect,input_quote=input_quote,expect_quote=expect_quote)
        self.actions.append(step)

    def basic_step(self,*commands,expect=None,input_quote='"',expect_quote='"'):
        """Adds a step by converting list of `commands` to a space-delimited string to run
        
        Args:
            *commands: ordered arguments to convert to a space-delimited string to run
            expect (str, optional): the command prompt to wait for before acting. Default determined by mode.
            quote (str, optional): The quote symbol to use (in case the other one is part of the string). Defaults to '"'. Not fully employed everywhere. Single quotes ensure no interpolation of the command.
        """

        if commands:
            command_str = " ".join([str(command) for command in commands if command])
            self.add_step(command_str,expect=expect,input_quote=input_quote,expect_quote=expect_quote)

    def insert_step(self,index,cmd,expect=None,input_quote='"',expect_quote='"'):
        """Adds a command to be run on the command line at a given index

        If `index` is greater than the current number of actions, behaves like `Scripter.add_step()`.
        
        Args:
            index (int): index at which to insert step
            cmd (str): the exact command to run
            expect (str, optional): the command prompt to wait for before acting. Default determined by mode.
            quote (str, optional): The quote symbol to use (in case the other one is part of the string). Defaults to '"'. Not fully employed everywhere. Single quotes ensure no interpolation of the command.
        """

        index = int(index)
        if index > len(self.actions) or index == -1:
            self.add_step(cmd=cmd,expect=expect,input_quote=input_quote,expect_quote=expect_quote)
            return
        elif index < 0: raise IndexError(f"Index should be greater than zero or -1")
        if not expect: expect = self.expect
        step = Step(cmd=cmd,expect=expect,input_quote=input_quote,expect_quote=expect_quote)
        self.actions = self.actions[0:index] + [step] + self.actions[index:]

    def is_empty(self):
        """True if no planned actions; false if any steps already exist"""

        return bool(self.actions)

    def get_steps(self,step_list:List[Step]=[],sep:str="\n"):
        """Joins all steps into string delimited by seperator
        
        Args:
            step_list (list[Step]): a list of step objects in the order they should be added
            sep (str): the string seperator used when joining steps into single string
        """

        if not step_list:
            step_list = self.actions
        return ''.join([step.__repr__(sep) for step in step_list])

    def _add_end_step(self):
        """Sends command to exit hpc. Prevents closing before done."""

        if self.mode == "sftp": end = "quit"
        elif self.mode == "ssh": end = "exit"
        # add end step if end step isn't already last step
        if not end in self.actions[-1].action:
            self.add_step(cmd=end)

    def __full_command(self):
        """Gets full `expect` command to run"""

        self._add_end_step()
        return self.open + self.entry + self.get_steps(self.__pw_steps) + self.get_steps() + self.close

    def get_actions(self):
        """Creates a generator yielding all desired actions in order"""
        for step in self.actions:
            # yield step.action.strip().replace('send "','').replace('"','') # original # TODO
            # yield step.action.strip().replace('send "','').replace('"','\\"') # new
            # yield repr(step.action.strip().replace('send "','').replace('"','\\"')) # new
            yield step.action.strip().replace('send "','')
    
    def preview_steps(self):
        """Prints all action steps in order to stdout"""

        print("\nCommand preview:")
        for action in enumerate(self.get_actions()):
            print(action)

    def clear(self):
        """Remove all actions"""

        self.actions:list[Step]=[]

    def run(self):
        """Runs all commands currently in self.actions"""

        # print("CMD:",self.__full_command())
        os.system(self.__full_command())

    def pwd(self):
        """Prints current working directory"""

        self.add_step("pwd")
    
    def ls(self,dir_name=None):
        """Prints contents of hpc directory (Default: current directory) to stdout"""

        if not dir_name: dir_name = "."
        self.basic_step("ls -la",dir_name)

    def mkdir(self,dir_name,local):
        """Changes working directory to `dir`
        
        Args:
            dir_name (str | Path): directory to change to
            local (bool): A flag indicating to change local working directory (not remote)
        """

        l = "l" if local else ""
        self.add_step(f"{l}mkdir {dir_name}")
    
    def cwd(self,dir_name,local=False):
        """Changes working directory to `dir`
        
        Args:
            dir_name (str | Path): directory to change to
            local (bool): A flag indicating to change local working directory (not remote)
        """

        if local==True:
            if self.mode == "sftp":
                cd = "lcd"
            else:
                raise Exception("lcd only works with sftp")
        else: cd = "cd" 
        self.basic_step(cd,dir_name)

    def set_permissions(self,files,group:str=None,octal:str="0664"):
        """WARNING: Test before use
        
        Changes permissions (default: 0664 = rw-rw-r--) and group name (if provided) of a file.
        Octal numbers must be used for sftp, not text
        Known past issue:
            May cause files to become unreachable, usually only when setting permissions for directories.
            Best results if setting permissions for specific files (rather than whole directories).
            All permissions become question marks.
            To Fix: Try manually getting and putting files via sftp sometimes fixes this

        Args:
            files (str | list): files for which to change permissions
            group (str | None): group used for `chgrp` command (if provided)
            octal (str | int): permission level
        """

        if type(files) == str: files = [files]
        if not self.group and group!="": self.group = group
        if self.mode == 'sftp':
            for n,x in {"group":self.group,"octal":octal}.items():
                # print(x, type(x))
                if type(x) == int: x = str(x)
                if type(x) == str and not x.isnumeric() and x:
                    raise TypeError(f"Invalid input ({x}, type:{type(x)}) for {n}. Numeric values must be used over sftp.")
        for file in files:
            self.basic_step("chmod",octal,file)
            if self.group:
                self.basic_step("chgrp",self.group,file)

    def directory_transfer_check(self,file):
        """Returns True if it looks like a directory is being transferred

        Args:
            file (str | Path): name of file(s) to transfer
        """

        return "*" in Path(file).name

    def transfer(self,trans_type,file,outdir=None,local=False,new_name=None,options:list=[]):
        """Transfer file to/from outdir over sftp,

        Only transfer files, not directories. To move all files in a directory, use `file="directory/*"`
        
        Args:
            trans_type (str): command to use (options: [get, put])
            file (str | Path): path to file to transfer
            outdir (str | Path): directory where transferred file(s) will live
            local (bool): a flag to indicate that the transferred file is moving to a local destination
            new_name (str): name of transferred file (or directory if transferring multiple files). If not provided, `new_name` will be set to `outdir`/`file`.
            options (list): options to apply to the `get` or `set` command
        """

        # only allow transfers via sftp
        if self.mode != "sftp": raise Exception(f"'{trans_type}' can only be used with mode='sftp'")
        globbed_directory = self.directory_transfer_check(file)
        # determine name of outfile/new_file, if not provided
        if globbed_directory:
            if outdir:
                temp = Path(outdir)
                if not new_name:
                    new_name = temp.name + "/"
                    outdir = temp.parent
            else:
                if not new_name:
                    # ignore the glob pattern in file.name
                    new_name = Path(file).parent.name + "/"
            # attempt to make `new_name` directory if it looks like we're transferring a directory's contents
            self.mkdir(new_name,local=local)
        else:
            if new_name == None:
                new_name = Path(file).name
        # go to `outdir` where `newfile` (file or directory) will live (or else assume cwd is outdir)
        if outdir:
            self.cwd(dir_name=outdir,local=local)

        # TEMP: TODO remove
        self.add_step("pwd")
        # add transfer step
        if options:
            opt="-"+"".join(options)
            self.basic_step(trans_type,opt,file,new_name,"\n")
        else:
            self.basic_step(trans_type,file,new_name,"\n")

    def get(self,file,outdir=None,new_name=None,options:list=[]):
        """Downloads file to current local directory or specified local outdir,

        Only transfer files, not directories. To move all files in a directory, use `directory/*`
        
        Each `get` consists of 2 steps:
            If outdir is provided:
                `cd "${outdir}"`
            Regardless:
                `get "${file}" "${new_name}"`

        Args:
            file (str | Path): file to transfer
            outdir (str | Path): directory where file will end up
            new_name (str): If provided, `file` will be renamed to `outdir`/`new_name`
            options (list): options to apply to the `get` command
            is_dir (bool): A flag to indicate that `file` is a directory
        """

        self.transfer("get",file,outdir,local=True,new_name=new_name,options=options)

    def put(self,file,outdir=None,new_name=None,options:list=[],set_permissions=False):
        """Uploads file to current remote directory or specified remote outdir,

        Only transfer files, not directories. To move all files in a directory, use `directory/*`
        
        Each `put` consists of 3 main steps:
            If outdir is provided:
                `mkdir ${outdir};`
                `cd "${outdir}";`
            Regardless:
                `get "${file}" "${new_name}";`
            ``
        Args:
            file (str | Path): file to transfer
            outdir (str | Path): directory where file will end up
            new_name (str): If provided, `file` will be renamed to `outdir`/`new_name`
            options (list): options to apply to the `set` command
            set_permissions (bool): A flag indicating to include permission changing steps
            is_dir (bool): A flag to indicate that `file` is a directory
        """

        if outdir:
            self.add_step(f"mkdir {outdir}") # mkdir if not present (will throw error if exists, but that's okay)
        self.transfer("put",file,outdir,local=False,new_name=new_name,options=options)
        if set_permissions == True:
            self.set_permissions(str(Path(outdir)/Path(file).name))

    ### Get login info
    def write_credentials(self):
        """Writes provided credentials to config"""

        self.config.parent.mkdir(exist_ok=True,parents=True)
        with self.config.open("w") as out:
            out.write(f"username={self.username}\n")
            out.write(f"password={self.__password}\n")

    def _get_credential_if_present(self,line,cred):
        """Sets credentials (if found in `line`) to associated `cred` attribute"""

        if cred in line.lower():
            attr = line.split("=")[-1].strip()
            if cred=="password": self.__password = attr
            else: setattr(self,cred,attr)

    def read_credentials(self,config:Path):
        """Gathers credentials from `config`, if present
        
        Args:
            config (str | Path): path to config file containing credentials like
            
            '''

            username=myuser

            password=mypass

            '''
        """

        with config.open() as fh:
            for line in fh:
                line = line.strip()
                for cred in ('username','password','group','site'):
                    self._get_credential_if_present(line,cred)

    def request_credentials(self,reset_user=False,reset_pass=False):
        """Asks for any missing credentials
        
        Args:
            reset_user (bool): A flag to rewrite `config` with new `username`
            reset_pass (bool): A flag to rewrite `config` with new `password`
        """

        print("Collecting your cluster login information to speed up future interactions:")
        if not self.username or reset_user==True:
            self.username = input("Username:\n> ")
            print(f"The username you entered is: {self.username}")
            user_ok = input("Is this correct? (Y/n)\n> ")
            if user_ok.strip().lower()=="n":
                self.request_credentials(reset_user=True)
        if not self.__password or reset_pass==True:
            self.__password = getpass("Password:\n> ")
        if not self.group:
            self.group = input("Enter a group name (or octal - must be octal for sftp) for permissions-setting or skip by hitting enter:\n> ")
        if not self.site:
            self.site = input("Enter the site you're trying to reach:\n> ")

    def reset_username(self):
        """Gets `username` and resets in `config`"""

        self.request_credentials(reset_user=True)
        self.write_credentials()

    def reset_password(self):
        """Gets `password` and resets in `config`"""

        self.request_credentials(reset_pass=True)
        self.write_credentials()

    def get_credentials(self,save=True,overwrite=False,headless=False):
        """Gets credentials passed in at instantiation or looks for them in config or requests them
        
        Args:
            save (bool): A flag to save credentials in `config`
            overwrite (bool): A flag to overwrite `config` file with current credentials
            headless (bool): A flag to prevent any interactive requests for information

        Returns:
            username,password
        """

        if self.config:
            # deal with expansion of "~" in desired config path
            if Path("~") in list(self.config.parents):
                if str(self.config)[0] != "~":
                    raise Exception("Config path looks weird:",self.config)
                else:
                    self.config = Path(str(self.config).replace("~",str(Path.home())))
        else:
            self.config = Path.home() / ".pooPatrol/hpc_config.txt"
            self.config = self.config.resolve()
        if not self.username or not self.__password:
            if self.config.exists():
                self.read_credentials(self.config)
                self.get_credentials() # verify that username/password were found
            else:
                if headless == True:
                    print(f"Config file '{self.config}' is missing variables\n"
                        f"It should look like this:\n"
                        f"username=youruser\n"
                        f"password=yourpass\n\n"
                        f"Or you need to pass in a username and/or password at {self.__class__.__name__} instantiation.")
                    exit(1)
                else:
                    print(f"Requested config not found ({self.config}).\nGathering credentials...")
                    self.request_credentials()
        if save and not self.config.exists() or overwrite:
            print(f"Writing out credentials to {self.config}")
            self.write_credentials()
        return self.username,self.__password
