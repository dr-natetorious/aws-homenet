@ECHO OFF
@ECHO ==================================
@ECHO Local Debug Script
@ECHO Nate Bachmeier
@ECHO ==================================

@SETLOCAL enableextensions enabledelayedexpansion
@SET base_path=%~dp0

@SET TDA_CLIENT_ID=LBKWZPV2F81HNYHCLAMBWDZGOUCEQICV
@SET TDA_REDIRECT_URI=https://9mv1jn55kf.execute-api.us-west-2.amazonaws.com/prod/connect
@SET AWS_DEFAULT_REGION=us-west-2
@SET TDA_SECRET_ID=arn:aws:secretsmanager:us-west-2:581361757134:secret:SecretsLayerTDASECRET4460BB-UMsShhBc3uqf-M1Pzwn
@SET STREAM_NAME=finsurf-incoming-quotes

python %base_path%\get_quotes.py

