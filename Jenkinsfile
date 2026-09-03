pipeline{
    agent any   

    stages{
        stage("checkout"){
            steps{
                checkout scm
            }
        }
        stage("build"){
            steps{
                echo "Building Rag Chatbot"
            }
        }
        stage("Test"){
            steps{
                echo "Running Test"
            }
        }
    }
}