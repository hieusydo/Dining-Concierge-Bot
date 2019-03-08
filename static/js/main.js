$(document).ready(function() {
    handleAuth();
});

function handleInputSubmit(apigClient) {
    var outputArea = $("#chat-output");

    $("#user-input-form").submit(function(e) {
        var message = $("#user-input").val();
        // console.log(message);
        e.preventDefault();

        outputArea.append(`
        <div class='bot-message'>
        <div class='message'>
        ${message}
        </div>
        </div>
        `);
        $("html, body").animate({ scrollTop: $(document).height() }, 1000);
        $("#user-input").val("");

        var body = {
            "text": message,
            "timestamp": Date.now()
        };
        var params = {};
        var additionalParams = {
            headers: {},
            queryParams: {}
        };
        apigClient.chatbotPost(params, body, additionalParams)
        .then(function(result){
            console.log(result.status);
            console.log(result.data);

            var reply = result.data.body.message;

            outputArea.append(`
            <div class='user-message'>
            <div class='message'>
            ${reply}
            </div>
            </div>
            `);

        }).catch( function(err){
            console.log(err)
        });
    });
}

function tokenizeUrl() {
    var vars = {};
    var parts = window.location.href.replace(/[#?&]+([^=&]+)=([^&]*)/gi, function(m,key,value) {
        vars[key] = value;
    });
    return vars;
}

function handleAuth() {
    // Verify token from url
    urlTokens = tokenizeUrl()

    /* Use the idToken for Logins Map when Federating User Pools with identity pools or when passing through an Authorization Header to an API Gateway Authorizer */
    var idToken = urlTokens["id_token"];

    // Add the User's Id Token to the Cognito credentials login map.
    AWS.config.region = 'us-east-1';
    AWS.config.credentials = new AWS.CognitoIdentityCredentials({
        IdentityPoolId: 'us-east-1:70cecd11-2e47-4549-b880-f312d0332b21',
        Logins: {
            'cognito-idp.us-east-1.amazonaws.com/us-east-1_bOBoYMMfO': idToken
        }
    });

    //refreshes credentials using AWS.CognitoIdentity.getCredentialsForIdentity()
    AWS.config.credentials.refresh((error) => {
        if (error) {
            console.error(error);
        } else {
            // Instantiate aws sdk service objects now that the credentials have been updated.
            console.log('Successfully authenticated!');

            // Make the call to obtain credentials
            AWS.config.credentials.get(function(){

                // Credentials will be available when this function is called.
                var accessKeyId = AWS.config.credentials.accessKeyId;
                var secretAccessKey = AWS.config.credentials.secretAccessKey;
                var sessionToken = AWS.config.credentials.sessionToken;

                // console.log(accessKeyId, secretAccessKey)

                var apigClient = apigClientFactory.newClient({
                    accessKey: accessKeyId,
                    secretKey: secretAccessKey,
                    sessionToken: sessionToken
                });

                // console.log(apigClient);

                handleInputSubmit(apigClient);

            });
        }
    });
}