#!/bin/bash

MESSAGE="$1"
VERSION="$2"

if [ -z "$MESSAGE" ] || [ -z "$VERSION" ]; then
	echo "Usage:"
	echo "./release.sh \"commit message\" version"
	echo
	echo "Example:"
	echo "./release.sh \"fixed multiple HTML pages\" 0.2.1"
	exit 1
fi

echo "Releasing WebGUI $VERSION"
echo

# Check that we're in the git repository
if [ ! -d ".git" ]; then
	echo "Error: this is not a git repository."
	exit 1
fi

# Check that the version looks reasonable
if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
	echo "Error: version must look like 0.2.1"
	exit 1
fi

# Update version in pyproject.toml
sed -i '' "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml

echo "Version changed to $VERSION"
echo

# Show what is going to be committed
git status

echo
read -p "Continue with release? [y/N] " CONFIRM

if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
	echo "Release cancelled."
	exit 0
fi

# Add everything
git add .

# Commit
git commit -m "$MESSAGE"

if [ $? -ne 0 ]; then
	echo "Git commit failed."
	exit 1
fi

# Push commit
echo
echo "Pushing changes to GitHub..."

git push origin main

if [ $? -ne 0 ]; then
	echo "Git push failed."
	exit 1
fi

# Create release tag
echo
echo "Creating tag v$VERSION..."

git tag "v$VERSION"

if [ $? -ne 0 ]; then
	echo "Failed to create tag."
	exit 1
fi

# Push tag
echo
echo "Pushing tag to GitHub..."

git push origin "v$VERSION"

if [ $? -ne 0 ]; then
	echo "Failed to push tag."
	exit 1
fi

echo
echo "================================"
echo "Release $VERSION sent!"
echo "================================"
echo
echo "GitHub Actions should now build and publish it to PyPI."
echo
echo "Watch the GitHub Actions page to see the release."