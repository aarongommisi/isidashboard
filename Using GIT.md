Using GIT 

## Initialise GIT Repo:

From your terminal, run the following commands after navigating to the folder you would like to add.

```
git init
```

This step creates a hidden .git directory in your project folder, which the git software recognizes and uses to store all the metadata and version history for the project.


## Add files to GIT index

```
git add -A
``` 

The git add command is used to tell git which files to include in a commit, and the -A (or --all) argument means “include all”.


## Commit added files/changes

```
git commit -m 'Description of change'
```

The git commit command creates a new commit with all files that have been “added”. The -m (or --message) sets the message that will be included alongside the commit, used for future reference to understand the commit.

## Add a new remote origin

```
git remote add origin git@github.com:aarongommisi/isidashboard.git
```


## Push the update to GIT

```
git push -u -f origin main
```

he -u (or --set-upstream) flag sets the remote origin as the upstream reference. This allows you to later perform git push and git pull commands without having to specify an origin since we always want GitHub in this case.

The -f (or --force) flag stands for force. This will automatically overwrite everything in the remote directory.


## pulling updates to dev or live

Make sure to naviagte to the root of the project then run the command below
	
```
git pull git@github.com:aarongommisi/isidashboard.git
```

This will pull the latest commited changes to the local device or server the command is being run on. 


## View a changelog


	```
	git log

	or

	git whatchanged
	```