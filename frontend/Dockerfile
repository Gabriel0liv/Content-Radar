FROM node:20-alpine

# Set work directory
WORKDIR /app

# Copy dependency configs
COPY package.json package-lock.json ./

# Clean install dependencies using lock file
RUN npm ci

# Copy other application files
COPY . .

# Expose port
EXPOSE 3000

# Start development server binding to all interfaces
CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0"]
