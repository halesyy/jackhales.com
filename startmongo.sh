#!/usr/bin/env bash
set -euo pipefail

mongo_formula="${MONGO_FORMULA:-mongodb-community@8.0}"
mongo_port="${MONGO_LOCAL_PORT:-27017}"
mongo_uri="${MONGO_LOCAL_URI:-mongodb://127.0.0.1:$mongo_port}"

mongo_is_ready() {
  if command -v mongosh >/dev/null 2>&1; then
    mongosh --quiet "$mongo_uri" --eval 'quit(db.runCommand({ ping: 1 }).ok ? 0 : 1)' >/dev/null 2>&1
    return
  fi

  nc -z 127.0.0.1 "$mongo_port" >/dev/null 2>&1
}

if mongo_is_ready; then
  echo "MongoDB is already running at $mongo_uri"
  exit 0
fi

wait_for_mongo() {
  for _ in {1..30}; do
    if mongo_is_ready; then
      echo "MongoDB is ready at $mongo_uri"
      echo "Backend settings: MONGODB_URL=$mongo_uri MONGODB_DATABASE=jackhales_dev"
      exit 0
    fi
    sleep 1
  done
  echo "MongoDB did not become ready within 30 seconds." >&2
  exit 1
}

# A mongod already on PATH (installed outside Homebrew, or from another tap)
# is started directly, so nothing new needs installing.
if command -v mongod >/dev/null 2>&1 && ! { command -v brew >/dev/null 2>&1 && brew list --formula "$mongo_formula" >/dev/null 2>&1; }; then
  data_dir="${MONGO_LOCAL_DBPATH:-${TMPDIR:-/tmp}/jackhales-mongo}"
  mkdir -p "$data_dir"
  echo "Starting $(command -v mongod) with data in $data_dir..."
  mongod --dbpath "$data_dir" --port "$mongo_port" --bind_ip 127.0.0.1 --fork --logpath "$data_dir/mongod.log" >/dev/null
  wait_for_mongo
fi

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is required to install and start local MongoDB." >&2
  echo "Install it from https://brew.sh, then run this script again." >&2
  exit 1
fi

mongo_is_installed=false
if brew list --formula "$mongo_formula" >/dev/null 2>&1; then
  mongo_is_installed=true
else
  echo "Installing $mongo_formula..."
  brew tap mongodb/brew
fi

# Recent Homebrew versions require explicit trust before loading formulae
# from third-party taps. mongodb/brew is MongoDB's official Homebrew tap.
if brew trust --help >/dev/null 2>&1; then
  # mongodb-database-tools comes from the same tap and needs trust too.
  brew trust --formula "mongodb/brew/$mongo_formula" "mongodb/brew/mongodb-database-tools" >/dev/null
fi

if [[ "$mongo_is_installed" == false ]]; then
  brew install "$mongo_formula"
fi

echo "Starting $mongo_formula..."
brew services start "$mongo_formula"

for _ in {1..30}; do
  if mongo_is_ready; then
    echo "MongoDB is ready at $mongo_uri"
    echo "Backend settings: MONGODB_URL=$mongo_uri MONGODB_DATABASE=jackhales_dev"
    exit 0
  fi
  sleep 1
done

echo "MongoDB did not become ready within 30 seconds." >&2
echo "Check the service with: brew services info $mongo_formula" >&2
exit 1
