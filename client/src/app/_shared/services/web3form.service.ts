import {Injectable} from '@angular/core';
import { HttpClient } from "@angular/common/http";
import {Observable} from "rxjs";

@Injectable({
  providedIn: 'root'
})
export class Web3formService {
  web3formUrl = "https://api.web3forms.com/submit"

  constructor(private httpClient: HttpClient) {
  }

  sendEmail(formData: FormData): Observable<Object> {
    return this.httpClient.post(this.web3formUrl, formData)
  }
}
