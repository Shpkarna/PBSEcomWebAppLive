const appDatabase = process.env.MONGO_APP_DATABASE || 'ecomdb';
const logDatabase = process.env.MONGO_LOG_DATABASE || 'logDB';
const appUsername = process.env.MONGO_APP_USERNAME || 'ecom_app';
const appPassword = process.env.MONGO_APP_PASSWORD || 'ecom_password';

const adminDb = db.getSiblingDB('admin');
const appDb = db.getSiblingDB(appDatabase);
const logsDb = db.getSiblingDB(logDatabase);
const existingUser = adminDb.getUser(appUsername);

if (!appDb.getCollectionNames().includes('__bootstrap__')) {
  appDb.createCollection('__bootstrap__');
}

if (!logsDb.getCollectionNames().includes('__bootstrap__')) {
  logsDb.createCollection('__bootstrap__');
}

if (!existingUser) {
  adminDb.createUser({
    user: appUsername,
    pwd: appPassword,
    roles: [
      { role: 'dbOwner', db: appDatabase },
      { role: 'readWrite', db: appDatabase },
      { role: 'dbOwner', db: logDatabase },
      { role: 'readWrite', db: logDatabase },
    ],
  });

  print(`Created MongoDB application user ${appUsername}`);
} else {
  print(`MongoDB application user ${appUsername} already exists`);
}

appDb.__bootstrap__.updateOne(
  { _id: 'app-bootstrap' },
  { $set: { initializedAt: new Date() } },
  { upsert: true }
);

logsDb.__bootstrap__.updateOne(
  { _id: 'log-bootstrap' },
  { $set: { initializedAt: new Date() } },
  { upsert: true }
);

print(`Initialized MongoDB databases ${appDatabase} and ${logDatabase}`);