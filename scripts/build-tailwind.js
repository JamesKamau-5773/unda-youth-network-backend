#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const postcss = require('postcss');
const tailwind = require('@tailwindcss/postcss');
const autoprefixer = require('autoprefixer');

async function build() {
  const inputPath = path.resolve(__dirname, '../static/css/admin.css');
  const outputPath = path.resolve(__dirname, '../static/css/admin.build.css');
  const css = fs.readFileSync(inputPath, 'utf8');
  try {
    const result = await postcss([tailwind({ config: path.resolve(__dirname, '../tailwind.config.js') }), autoprefixer]).process(css, { from: inputPath });
    fs.writeFileSync(outputPath, result.css, 'utf8');
    console.log('Built', outputPath);
  } catch (err) {
    console.error('Build failed:', err);
    process.exit(1);
  }
}

build();
