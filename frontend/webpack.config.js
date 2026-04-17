const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const webpack = require('webpack');

module.exports = (env, argv) => {
  const packageOption = env?.packageOption || process.env.PACKAGE_OPTION;
  const validOptions = ['sandbox', 'trial', 'prod'];

  // For production builds, packageOption is mandatory
  if (argv?.mode === 'production') {
    if (!packageOption || !validOptions.includes(packageOption)) {
      console.error(
        '\n\x1b[31mERROR: --env packageOption is required for production builds.\x1b[0m\n' +
        'Usage: webpack --mode production --env packageOption=sandbox|trial|prod\n'
      );
      process.exit(1);
    }
  }

  return {
    target: ['web', 'es5'],
    entry: './src/index.tsx',
    output: {
      path: path.resolve(__dirname, 'dist'),
      filename: 'bundle.js',
      publicPath: '/',
      environment: {
        arrowFunction: false,
        const: false,
        destructuring: false,
        dynamicImport: false,
        forOf: false,
        module: false,
        optionalChaining: false,
        templateLiteral: false,
      },
    },
    module: {
      rules: [
        {
          test: /\.tsx?$/,
          use: {
            loader: 'ts-loader',
            options: {
              configFile: 'tsconfig.json',
            },
          },
          exclude: /node_modules/,
        },
        {
          test: /\.css$/,
          use: ['style-loader', 'css-loader'],
        },
      ],
    },
    resolve: {
      extensions: ['.tsx', '.ts', '.js'],
    },
    plugins: [
      new HtmlWebpackPlugin({
        template: './public/index.html',
      }),
      new webpack.DefinePlugin({
        'process.env.PACKAGE_OPTION': JSON.stringify(packageOption || 'sandbox'),
        'process.env.REACT_APP_API_URL': JSON.stringify(process.env.REACT_APP_API_URL || '/api'),
      }),
    ],
    devServer: {
      port: Number(process.env.PORT || 3000),
      historyApiFallback: true,
      hot: true,
      open: true,
      allowedHosts: 'all',
    },
  };
};
