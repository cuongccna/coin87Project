module.exports = {
  apps : [
    {
      name: "coin87-backend",
      cwd: "./backend",
      script: "venv/bin/uvicorn",
      args: "app.main:app --host 0.0.0.0 --port 9000",
      env: {
        PYTHONPATH: ".." // Set pythonpath to include backend directory
      }
    },
    {
      name: "coin87-frontend",
      cwd: "./frontend",
      script: "npm",
      args: "start -- -p 9001",
      env: {
        NODE_ENV: "production"
      }
    }
  ]
};
