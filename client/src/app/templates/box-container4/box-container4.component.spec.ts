import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BoxContainer4Component } from './box-container4.component';

describe('BoxContainer4Component', () => {
  let component: BoxContainer4Component;
  let fixture: ComponentFixture<BoxContainer4Component>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BoxContainer4Component]
    })
    .compileComponents();

    fixture = TestBed.createComponent(BoxContainer4Component);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
