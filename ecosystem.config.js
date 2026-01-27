module.exports = {
  apps : [
    {
      name: "coin87-backend",
      cwd: "./backend",
      script: "venv/bin/python",
      args: "-m uvicorn app.main:app --host 0.0.0.0 --port 9000",
      env: {
        PYTHONPATH: "."
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
