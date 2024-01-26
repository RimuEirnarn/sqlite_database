source ./bin/include/utility.bash

FILES="./bin/need-installed"

info "Installing pre-commit"
if [ ! -d .git/hooks ]; then
    mkdir .git/hooks
fi
cp $FILES/pre-commit ./.git/hooks/pre-commit

info "Refurbishing activation script"
acti=$(cat $FILES/activate)
here="$(pwd)"
printf "PROJECT_ROOT=\"$here\"\n" > ./bin/activate
printf "\n$acti" >> ./bin/activate
