#!/bin/bash

# Extract the version from buildVars.py
VERSION=$(grep '"addon_version"' buildVars.py | cut -d'"' -f4)

if [ -z "$VERSION" ]; then
  echo "Error: Could not retrieve version from buildVars.py"
  exit 1
fi

echo "Detected version: $VERSION"
read -p "Do you want to release this version? (y/n): " confirm

if [ "$confirm" != "y" ]; then
  echo "Release cancelled."
  exit 0
fi

# Check git status
echo "Checking git status..."
git fetch

# 1. Check if buildVars.py has uncommitted changes
if [ -n "$(git status --porcelain buildVars.py)" ]; then
  echo "Error: buildVars.py has uncommitted changes."
  exit 1
fi

# 2. Check if local branch is synchronized with origin/master
LOCAL_HASH=$(git rev-parse HEAD)
REMOTE_HASH=$(git rev-parse origin/master)

if [ "$LOCAL_HASH" != "$REMOTE_HASH" ]; then
  echo "Error: Local repository is not synchronized with origin/master."
  echo "Local: $LOCAL_HASH"
  echo "Remote: $REMOTE_HASH"
  exit 1
fi

# Check if the tag already exists
if git tag -l | grep -q "^$VERSION$"; then
  echo "Error: Tag $VERSION already exists."
  exit 1
fi

# Create the tag
echo "Creating tag $VERSION..."
git tag "$VERSION"
if [ $? -ne 0 ]; then
  echo "Error creating tag."
  exit 1
fi

# Push
echo "Pushing to origin..."
git push origin master --tags
if [ $? -ne 0 ]; then
  echo "Error pushing tags."
  exit 1
fi

echo "Version $VERSION released successfully."
exit 0
