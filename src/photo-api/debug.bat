@ECHO OFF
@ECHO ==================================
@ECHO Local Debug Script
@ECHO Nate Bachmeier
@ECHO ==================================

@SETLOCAL enableextensions enabledelayedexpansion
@SET base_path=%~dp0

@SET TDA_CLIENT_ID=LBKWZPV2F81HNYHCLAMBWDZGOUCEQICV
@SET TDA_REDIRECT_URI=https://9mv1jn55kf.execute-api.us-west-2.amazonaws.com/prod/connect
@SET AWS_REGION=us-west-2
@SET TDA_SECRET_ID=somevalue
@SET LOCAL_DEBUG=true
@SET FLASK_APP=handler.py
@SET FLASK_ENV=development



python -m flask run

