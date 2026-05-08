pipeline {
  agent any
  environment {
    KUNLUN_FAIL_ON = 'high'
    KUNLUN_INCLUDE_UNCONFIRM = '0'
    KUNLUN_WITH_VENDOR = '0'
  }
  stages {
    stage('Install') {
      steps {
        sh 'python -m pip install -r requirements.txt'
      }
    }
    stage('Scan') {
      steps {
        sh 'python tools/ci_scan.py --target . --output artifacts/kunlun-ci.json --fail-on "${KUNLUN_FAIL_ON}"'
      }
    }
  }
  post {
    always {
      archiveArtifacts artifacts: 'artifacts/kunlun-ci.json', allowEmptyArchive: true
    }
  }
}

